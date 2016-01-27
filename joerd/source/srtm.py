from bs4 import BeautifulSoup
from joerd.util import BoundingBox
from multiprocessing import Pool
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


SRTM_BASE_URL = 'http://e4ftl01.cr.usgs.gov/SRTM/SRTMGL1.003/2000.02.11/'


def __download_srtm_file(source_name, target_name, base_dir):
    url = SRTM_BASE_URL + "/" + source_name
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


def _download_srtm_file(source_name, target_name, base_dir):
    try:
        return __download_srtm_file(source_name, target_name, base_dir)
    except:
        print>>sys.stderr, "Caught exception: %s" % ("\n".join(traceback.format_exception(*sys.exc_info())))
        raise


def _parallel(func, iterable, num_threads=None):
    p = Pool(processes=num_threads)
    threads = []

    for x in iterable:
        p.apply_async(func, x)

    p.close()
    return_values = []
    for t in threads:
        return_values.append(t.get())

    p.join()
    return return_values


class SRTM:

    def __init__(self, regions, base_dir='srtm', num_download_threads=None):
        self.regions = regions
        self.num_download_threads = num_download_threads
        self.base_dir = base_dir

    def download(self):
        logger = logging.getLogger('srtm')
        logger.info('Fetching SRTM index...')
        r = requests.get(SRTM_BASE_URL)
        soup = BeautifulSoup(r.text, 'html.parser')

        is_srtm_file = re.compile(
            '^([NS])([0-9]{2})([EW])([0-9]{3}).SRTMGL1.hgt.zip$')

        links = []
        for a in soup.find_all('a'):
            link = a.get('href')
            if link is not None:
                m = is_srtm_file.match(link)
                if m:
                    bbox = self._parse_bbox(*m.groups())
                    if self._intersects(bbox):
                        fname = link.replace(".SRTMGL1.hgt.zip", ".hgt")
                        links.append((link, fname))

        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        logger.info("Starting download of %d SRTM files." % len(links))
        files = _parallel(_download_srtm_file,
                          [(l, f, self.base_dir) for l, f in links],
                          num_threads=self.num_download_threads)

        # sanity check
        for f in files:
            assert os.path.isfile(f)

        logger.info("Download complete.")

    def buildvrt(self):
        logger = logging.getLogger('srtm')
        logger.info("Creating VRT.")

        is_srtm_hgt = re.compile(
            '^([NS])([0-9]{2})([EW])([0-9]{3}).hgt$')
        files = []
        for f in glob.glob(os.path.join(self.base_dir, '*.hgt')):
            m = is_srtm_hgt.match(os.path.split(f)[1])
            if m:
                bbox = self._parse_bbox(*m.groups())
                if self._intersects(bbox):
                    files.append(f)

        args = ["gdalbuildvrt", "-q", self.vrt_file()] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        assert os.path.isfile(self.vrt_file())

        logger.info("VRT created.")

    def vrt_file(self):
        return os.path.join(self.base_dir, "srtm.vrt")

    def mask_negative(self):
        return True

    def filter_type(self):
        return gdal.GRA_Lanczos

    def _parse_bbox(self, is_ns, ns_deg, is_ew, ew_deg):
        bottom = int(ns_deg)
        left = int(ew_deg)

        if is_ns == 'S':
            bottom = -bottom
        if is_ew == 'W':
            left = -left

        return BoundingBox(left, bottom, left + 1, bottom + 1)

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox):
                return True
        return False


def create(regions):
    return SRTM(regions)
