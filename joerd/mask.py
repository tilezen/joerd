from osgeo import gdal
import numpy
import numpy.ma

def negative(src_filename, dst_driver, dst_filename):
    """
    Processes a raster which has valid positive heights, but invalid heights
    at less than or equal to zero. These zero or negative heights are masked
    to NODATA, and the file is written to dst_filename using dst_driver.
    """

    src_ds = gdal.Open(src_filename)
    mem_drv = gdal.GetDriverByName("MEM")
    ds = mem_drv.CreateCopy('', src_ds)
    x_size = ds.RasterXSize
    y_size = ds.RasterYSize

    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()

    data = band.ReadAsArray(0, 0, x_size, y_size)
    mask = (data <= 0) | (data == nodata)
    mx = numpy.ma.masked_array(data, mask=mask)
    res = band.WriteArray(numpy.ma.filled(mx, nodata))
    assert res == gdal.CPLE_None

    drv = gdal.GetDriverByName(dst_driver)
    dst_ds = drv.CreateCopy(dst_filename, ds)

    del dst_ds
    del ds
    del src_ds


def raster(src_filename, msk_filename, mask_value, dst_driver, dst_filename):
    """
    Processes a raster which is masked by a particular value of another raster.
    Both must be downloaded, but then they are masked at source - which
    requires both to be the same size, location and in the same projection.
    """

    orig_ds = gdal.Open(src_filename)
    mem_drv = gdal.GetDriverByName("MEM")
    src_ds = mem_drv.CreateCopy('', orig_ds)
    msk_ds = gdal.Open(msk_filename)

    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize
    assert x_size == msk_ds.RasterXSize
    assert y_size == msk_ds.RasterYSize
    assert src_ds.GetProjection() == msk_ds.GetProjection()
    assert src_ds.GetGeoTransform() == msk_ds.GetGeoTransform()

    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()

    src_data = src_band.ReadAsArray(0, 0, x_size, y_size)
    msk_data = msk_ds.GetRasterBand(1).ReadAsArray(0, 0, x_size, y_size)
    mask = (msk_data == mask_value)
    mx = numpy.ma.masked_array(src_data, mask=mask)
    res = src_band.WriteArray(numpy.ma.filled(mx, src_nodata))
    assert res == gdal.CPLE_None

    drv = gdal.GetDriverByName(dst_driver)
    dst_ds = drv.CreateCopy(dst_filename, src_ds)

    del dst_ds
    del msk_ds
    del src_ds
    del orig_ds


def raw(src_filename, raw_filename, raw_value, dst_driver, dst_filename):
    """
    Processes a raster which is masked by a particular value of a raw file.
    Both must be downloaded, but then they are masked at source - which
    requires both to be the same size, location and in the same projection.
    """

    orig_ds = gdal.Open(src_filename)
    mem_drv = gdal.GetDriverByName("MEM")
    src_ds = mem_drv.CreateCopy('', orig_ds)

    x_size = src_ds.RasterXSize
    y_size = src_ds.RasterYSize

    raw_data = numpy.reshape(numpy.fromfile(raw_filename, dtype=numpy.uint8),
                             (y_size, x_size), order='C')
    assert x_size == raw_data.shape[1]
    assert y_size == raw_data.shape[0]

    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()

    src_data = src_band.ReadAsArray(0, 0, x_size, y_size)
    mask = (raw_data == raw_value)
    mx = numpy.ma.masked_array(src_data, mask=mask)
    res = src_band.WriteArray(numpy.ma.filled(mx, src_nodata))
    assert res == gdal.CPLE_None

    drv = gdal.GetDriverByName(dst_driver)
    dst_ds = drv.CreateCopy(dst_filename, src_ds)

    del dst_ds
    del src_ds
    del orig_ds
