from joerd import vrt
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


def _mk_image(src_ds, dst_ds, filter_type):
    src_srs_wkt = src_ds.GetProjection()
    src_gt = src_ds.GetGeoTransform()
    src_x_res = abs(src_gt[1])
    src_y_res = abs(src_gt[5])

    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()

    dst_x_size = dst_ds.RasterXSize
    dst_y_size = dst_ds.RasterYSize
    dst_band = dst_ds.GetRasterBand(1)
    dst_nodata = dst_band.GetNoDataValue()
    dst_srs_wkt = dst_ds.GetProjection()

    f_type = filter_type(min(src_x_res, src_y_res))
    res = gdal.ReprojectImage(src_ds, dst_ds, src_srs_wkt,
                              dst_srs_wkt, f_type, 1024, 0.125)
    assert res == gdal.CPLE_None


_NUMPY_TYPES = {
    gdal.GDT_Int16: numpy.int16,
    gdal.GDT_Float32: numpy.float32
}


# compose a series of layers into a destination datasource.
#
# layers should be listed in order of increasing detail, as each will be
# painted on top of the last (except for nodata parts).
#
# dst_ds will be erased to its nodata value before composition starts.
#
def compose(tile, dst_ds, logger, dst_res):
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
    # WATCH OUT! numpy shapes are confusingly the "wrong" way around, that
    # is they are (height, width)!
    dst_band.WriteArray(
        numpy.full((dst_y_size, dst_x_size), dst_nodata, numpy_type))

    # we'll hold temporary reprojected layers in memory, so we need a
    # memory driver to hold all of that.
    mem_drv = gdal.GetDriverByName("MEM")
    assert mem_drv is not None

    # loop over layers in order, so the first layer will be overwritten
    # by any valid data values in later layers. so layers should be listed
    # in order of increasing detail.
    for source in tile.sources:
        logger.debug("Processing layer %s VRT", type(source).__name__)

        mem_ds = mem_drv.Create('', dst_x_size, dst_y_size, 1, dst_type)
        assert mem_ds is not None
        mem_ds.SetGeoTransform(dst_gt)
        mem_ds.SetProjection(dst_srs)
        mem_band = mem_ds.GetRasterBand(1)

        def _filter_type_func(src_res):
            return source.filter_type(src_res, dst_res)

        vrts = source.vrts_for(tile)
        for rasters in vrts:
            # set the memory buffer to be all nodata, which will be
            # overwritten by the call to _mk_image.
            mem_band.SetNoDataValue(dst_nodata)
            mem_band.WriteArray(
                numpy.full((dst_y_size, dst_x_size), dst_nodata, numpy_type))

            # build a VRT of just the overlapping tiles, then generate
            # the output image.
            with vrt.build([r.output_file() for r in rasters],
                           source.srs().ExportToWkt()) as src_ds:
                _mk_image(src_ds, mem_ds, _filter_type_func)

            # extract the output data, but only those which are not nodata,
            # and overwrite those pixels in the dst. the pixels which are
            # nodata in the VRT will stay nodata in the output.
            mem_band = mem_ds.GetRasterBand(1)
            mem_data = mem_band.ReadAsArray(0, 0, dst_x_size, dst_y_size)
            nodata = mem_band.GetNoDataValue()

            dst_data = dst_band.ReadAsArray(0, 0, dst_x_size, dst_y_size)
            nodata_test = numpy.equal(mem_data, nodata)
            new_data = numpy.choose(nodata_test, (mem_data, dst_data))
            res = dst_band.WriteArray(new_data)
            assert res == gdal.CPLE_None

    logger.debug("Done composite.")
