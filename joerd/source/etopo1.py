from joerd.util import BoundingBox
from contextlib import closing
from shutil import copyfile
import os.path
import os
import requests
import logging
import re
import tempfile
import sys
import zipfile
import traceback
import subprocess
import glob
from osgeo import gdal


ETOPO1_URL = 'https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/' \
             'bedrock/grid_registered/georeferenced_tiff/' \
             'ETOPO1_Bed_g_geotiff.zip'


WGS84_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,' \
            '298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0]' \
            ',AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY[' \
            '"EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY[' \
            '"EPSG","9108"]],AUTHORITY["EPSG","4326"]]'


def _download_etopo1_file(target_name, base_dir):
    url = ETOPO1_URL
    output_file = os.path.join(base_dir, target_name)

    if os.path.isfile(output_file):
        return output_file

    with closing(tempfile.NamedTemporaryFile()) as tmp:
        with closing(requests.get(url, stream=True)) as req:
            for chunk in req.iter_content(chunk_size=10240):
                if chunk:
                    tmp.write(chunk)
        tmp.flush()

        with zipfile.ZipFile(tmp.name, 'r') as zfile:
            zfile.extract(target_name, base_dir)

    return output_file


class ETOPO1:

    def __init__(self, base_dir='etopo1'):
        self.base_dir = base_dir

    def download(self):
        logger = logging.getLogger('etopo1')
        logger.info("Starting ETOPO1 download, this may take some time...")
        file = _download_etopo1_file('ETOPO1_Bed_g_geotiff.tif', self.base_dir)
        assert os.path.isfile(file)
        logger.info("Download complete.")

    def buildvrt(self):
        logger = logging.getLogger('etopo1')
        logger.info("Creating VRT.")

        # ETOPO1 covers the whole world
        files = glob.glob(os.path.join(self.base_dir, '*.tif'))

        args = ["gdalbuildvrt", "-q", "-a_srs", WGS84_WKT, \
                self.vrt_file()] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        assert os.path.isfile(self.vrt_file())

        logger.info("VRT created.")

    def vrt_file(self):
        return os.path.join(self.base_dir, "etopo1.vrt")

    def mask_negative(self):
        return False

    def filter_type(self):
        return gdal.GRA_Lanczos


def create(regions):
    return ETOPO1()
