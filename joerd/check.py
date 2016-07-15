import zipfile
import tarfile
from osgeo import gdal


def is_zip(tmp):
    """
    Returns True if the NamedTemporaryFile given as the argument appears to be
    a well-formed Zip file.
    """

    try:
        zip_file = zipfile.ZipFile(tmp.name, 'r')
        test_result = zip_file.testzip()
        return test_result is None

    except:
        pass

    return False


def is_tar_gz(tmp):
    """
    Returns True if the NamedTemporaryFile given as the argument appears to be
    a GZip-encoded TAR file.
    """

    try:
        tar = tarfile.open(tmp.name, mode='r:gz', errorlevel=2)
        names = [info.name for info in tar]
        return True

    except (tarfile.TarError, IOError, OSError) as e:
        return False


def is_gdal(tmp):
    """
    Returns true if the NamedTemporaryFile given as the argument appears to be
    a well-formed GDAL raster file.
    """

    try:
        ds = gdal.Open(tmp.name)
        band = ds.GetRasterBand(1)
        band.ComputeBandStats()
        return True

    except:
        pass

    return False
