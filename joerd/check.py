import zipfile
import tarfile
import shutil
import tempfile
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


def tar_gz_has_gdal(member_name):
    """
    Returns a function which, when called with a NamedTemporaryFile, returns
    True if that file is a GZip-encoded TAR file containing a `member_name`
    member which can be opened with GDAL.
    """

    def func(tmp):
        try:
            tar = tarfile.open(tmp.name, mode='r:gz', errorlevel=2)
            with tempfile.NamedTemporaryFile() as tmp_member:
                shutil.copyfileobj(tar.extractfile(member_name), tmp_member)
                tmp_member.seek(0)
                return is_gdal(tmp_member)

        except (tarfile.TarError, IOError, OSError) as e:
            return False

    return func


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
