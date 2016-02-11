from bs4 import BeautifulSoup
from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
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
import yaml
import time


IS_SRTM_FILE = re.compile(
    '^([NS])([0-9]{2})([EW])([0-9]{3}).SRTMGL1.hgt.zip$')


class SRTMTile(object):
    def __init__(self, parent, link, fname, bbox):
        self.parent = parent
        self.link = link
        self.fname = fname
        self.bbox = bbox

    def __key(self):
        return (self.link, self.fname, self.bbox)

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.__key() == b.__key()

    def __hash__(self):
        return hash(self.__key())

    def url(self):
        return self.parent.url + "/" + self.link

    def verifier(self):
        return check.is_zip

    def options(self):
        return self.parent.download_options

    def output_file(self):
        return os.path.join(self.parent.base_dir, self.fname)

    def unpack(self, tmp):
        with zipfile.ZipFile(tmp.name, 'r') as zfile:
            zfile.extract(self.fname, self.parent.base_dir)


class SRTM(object):

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'srtm')
        self.url = options['url']
        self.download_options = download.options(options)
        self.index_cache = None

    def get_index(self):
        index_file = os.path.join(self.base_dir, 'index.yaml')
        # if index doesn't exist, or is more than 24h old
        if not os.path.isfile(index_file) or \
           time.time() > os.path.getmtime(index_file) + 86400:
            self.download_index(index_file)

    def download_index(self, index_file):
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        logger = logging.getLogger('srtm')
        logger.info('Fetching SRTM index...')
        r = requests.get(self.url)
        soup = BeautifulSoup(r.text, 'html.parser')

        links = []
        for a in soup.find_all('a'):
            link = a.get('href')
            if link is not None:
                bbox = self._parse_bbox(link)
                if bbox:
                    fname = link.replace(".SRTMGL1.hgt.zip", ".hgt")
                    links.append(dict(link=link, fname=fname, bbox=bbox.bounds))

        with open(index_file, 'w') as f:
            f.write(yaml.dump(links))

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the SRTM scale, then there's no
        # point in including SRTM, it'll be far too fine to make a difference.
        # SRTM is 1 arc second.
        if tile.max_resolution() > 20 * 1.0 / 3600:
            return tiles

        # buffer by 0.01 degrees (36px) to grab neighbouring tiles and ensure
        # that there aren't any boundary artefacts.
        tile_bbox = tile.latlon_bbox().buffer(0.01)

        links = self.index_cache
        if links is None:
            index_file = os.path.join(self.base_dir, 'index.yaml')
            with open(index_file, 'r') as f:
                links = yaml.load(f.read())
            self.index_cache = links

        for link in links:
            bbox = BoundingBox(*link['bbox'])
            if tile_bbox.intersects(bbox):
                tiles.add(SRTMTile(self, link['link'], link['fname'], bbox))

        return tiles

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

    def mask_negative(self):
        return True

    def srs(self):
        return srs.wgs84()

    def _parse_bbox(self, link):
        m = IS_SRTM_FILE.match(link)
        if not m:
            return None

        is_ns, ns_deg, is_ew, ew_deg = m.groups()
        bottom = int(ns_deg)
        left = int(ew_deg)

        if is_ns == 'S':
            bottom = -bottom
        if is_ew == 'W':
            left = -left

        return BoundingBox(left, bottom, left + 1, bottom + 1)


def create(options):
    return SRTM(options)
