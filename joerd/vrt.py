from osgeo import gdal
from contextlib2 import contextmanager, closing
import subprocess
import tempfile
import logging


@contextmanager
def build(files, srs):
    with closing(tempfile.NamedTemporaryFile(suffix='.vrt')) as vrt:
        args = ["gdalbuildvrt", "-q", "-a_srs", srs, vrt.name ] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        ds = gdal.Open(vrt.name)
        yield ds
        del ds
