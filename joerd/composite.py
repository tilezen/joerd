from osgeo import osr, gdal
import numpy
import numpy.ma
import sys


def _tx_bbox(tx, bbox, expand=0.0):
    xs = []
    ys = []
    for i in range(0,4):
        ix = float(bbox[i & 2])
        iy = float(bbox[(i & 1) * 2 + 1])
        x, y, z = tx.TransformPoint(ix, iy)
        xs.append(x)
        ys.append(y)
    bbox = (min(xs), min(ys), max(xs), max(ys))
    xspan = bbox[2] - bbox[0]
    yspan = bbox[3] - bbox[1]
    return (bbox[0] - 0.5 * expand * xspan,
            bbox[1] - 0.5 * expand * yspan,
            bbox[2] + 0.5 * expand * xspan,
            bbox[3] + 0.5 * expand * yspan)


def _mk_image(infile, dst_ds, dst_bbox, mask_negative, filter_type):
    src_ds = gdal.Open(infile)

    src_srs = osr.SpatialReference()
    src_srs_wkt = src_ds.GetProjection()
    assert src_srs_wkt, "Need a valid source SRS, not %r" % src_srs_wkt
    src_srs.ImportFromWkt(src_srs_wkt)
    dst_srs = osr.SpatialReference()
    dst_srs_wkt = dst_ds.GetProjection()
    assert dst_srs_wkt, "Need a valid destination SRS, not %r" % dst_srs_wkt
    dst_srs.ImportFromWkt(dst_srs_wkt)

    rev_tx = osr.CoordinateTransformation(dst_srs, src_srs)
    src_bbox = _tx_bbox(rev_tx, dst_bbox, 0.1)

    src_gt = src_ds.GetGeoTransform()
    src_x_res = abs(src_gt[1])
    src_y_res = abs(src_gt[5])

    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()

    res = gdal.ReprojectImage(src_ds, dst_ds, src_srs.ExportToWkt(),
                              dst_srs.ExportToWkt(), filter_type,
                              1024, 0.125)
    assert res == gdal.CPLE_None

    dst_x_size = dst_ds.RasterXSize
    dst_y_size = dst_ds.RasterYSize
    dst_band = dst_ds.GetRasterBand(1)
    dst_nodata = dst_band.GetNoDataValue()

    if mask_negative:
        dst_data = dst_band.ReadAsArray(0, 0, dst_x_size, dst_y_size)
        dst_mask = (dst_data <= 0) | (dst_data == src_nodata)
        mx = numpy.ma.masked_array(dst_data, mask=dst_mask)
        res = dst_band.WriteArray(numpy.ma.filled(mx, dst_nodata))
        assert res == gdal.CPLE_None


_NUMPY_TYPES = {
    gdal.GDT_Int16: numpy.int16
}


# compose a series of layers into a destination datasource.
#
# layers should be listed in order of increasing detail, as each will be
# painted on top of the last (except for nodata parts).
#
# dst_ds will be erased to its nodata value before composition starts.
#
def compose(layers, dst_ds, dst_bbox, logger):
    dst_band = dst_ds.GetRasterBand(1)
    dst_nodata = dst_band.GetNoDataValue()
    dst_x_size = dst_ds.RasterXSize
    dst_y_size = dst_ds.RasterYSize
    dst_gt = dst_ds.GetGeoTransform()
    dst_srs = dst_ds.GetProjection()

    # figure out what numpy type corresponds to the data type of the layer
    # we're compositing.
    dst_type = dst_band.DataType
    numpy_type = _NUMPY_TYPES.get(dst_type)
    assert numpy_type is not None, "Unable to compose type %r" % \
        dst_band.GetUnitType()

    # write the nodata value to blank out the source dataset
    dst_band.WriteArray(
        numpy.full((dst_x_size, dst_y_size), dst_nodata, numpy_type))

    # we'll hold temporary reprojected layers in memory, so we need a
    # memory driver to hold all of that.
    mem_drv = gdal.GetDriverByName("MEM")
    assert mem_drv is not None

    # loop over layers in order, so the first layer will be overwritten
    # by any valid data values in later layers. so layers should be listed
    # in order of increasing detail.
    for layer in layers:
        logger.info("Processing layer VRT: %r", layer.vrt_file())

        mem_ds = mem_drv.Create('', dst_x_size, dst_y_size, 1, dst_type)
        assert mem_ds is not None
        mem_ds.SetGeoTransform(dst_gt)
        mem_ds.SetProjection(dst_srs)
        mem_band = mem_ds.GetRasterBand(1)
        mem_band.SetNoDataValue(dst_nodata)
        mem_band.WriteArray(
            numpy.full((dst_x_size, dst_y_size), dst_nodata, numpy_type))

        filter_type = layer.filter_type()
        vrt_file = layer.vrt_file()
        _mk_image(layer.vrt_file(), mem_ds, dst_bbox, layer.mask_negative(),
                  layer.filter_type())

        mem_band = mem_ds.GetRasterBand(1)
        mem_data = mem_band.ReadAsArray(0, 0, dst_x_size, dst_y_size)
        nodata = mem_band.GetNoDataValue()

        dst_data = dst_band.ReadAsArray(0, 0, dst_x_size, dst_y_size)
        nodata_test = numpy.equal(mem_data, nodata)
        new_data = numpy.choose(nodata_test, (mem_data, dst_data))
        res = dst_band.WriteArray(new_data)
        assert res == gdal.CPLE_None

    logger.info("Done composite.")
