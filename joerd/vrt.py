from osgeo import gdal
from contextlib2 import contextmanager, closing
import subprocess
import tempfile
import logging
import os.path


@contextmanager
def build(files, srs):
    with closing(tempfile.NamedTemporaryFile(suffix='.vrt')) as vrt:
        # ensure files are actually present before trying to make a VRT from
        # them.
        for f in files:
            assert os.path.exists(f), "Trying to build a VRT including file " \
                "%r, but it does not seem to exist." % f

        args = ["gdalbuildvrt", "-q", "-a_srs", srs, vrt.name ] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        ds = gdal.Open(vrt.name)
        yield ds
        del ds
