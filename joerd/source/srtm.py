from bs4 import BeautifulSoup
from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.index as index
import joerd.mask as mask
import joerd.tmpdir as tmpdir
from contextlib2 import closing, ExitStack
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

    def urls(self):
        url_list = [self.parent.url + "/" + self.link]
        if self.parent.mask_url:
            mask_link = self.link.replace(".SRTMGL1.hgt", ".SRTMSWBD.raw")
            url_list.append(self.parent.mask_url + "/" + mask_link)
        return url_list

    def verifier(self):
        return check.is_zip

    def options(self):
        return self.parent.download_options

    def output_file(self):
        return os.path.join(self.parent.base_dir, self.fname)

    def unpack(self, data_zip, mask_zip):
        with tmpdir.tmpdir() as d:
            with zipfile.ZipFile(data_zip.name, 'r') as zfile:
                zfile.extract(self.fname, d)

            mask_name = self.fname.replace(".hgt", ".raw")
            with zipfile.ZipFile(mask_zip.name, 'r') as zfile:
                zfile.extract(mask_name, d)

            mask_file = os.path.join(d, mask_name)
            # mask off the water using the mask raster raw file
            mask.raw(os.path.join(d, self.fname), mask_file, 255,
                     "SRTMHGT", self.output_file())


def _parse_srtm_tile(link, parent):
    fname = link.replace(".SRTMGL1.hgt.zip", ".hgt")
    bbox = parent._parse_bbox(link)
    return SRTMTile(parent, link, fname, bbox)


class SRTM(object):

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'srtm')
        self.url = options['url']
        self.mask_url = options.get('mask-url')
        self.download_options = download.options(options)
        self.tile_index = None

    # Pickling the tile index is probably not a good idea, since it is
    # an FFI / C object. Setting it to None should cause it to be
    # regenerated post-unpickle.
    def __getstate__(self):
        odict = self.__dict__.copy()
        odict['tile_index'] = None
        return odict

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
                    links.append(link)

        with open(index_file, 'w') as f:
            f.write(yaml.dump(links))

    def _ensure_tile_index(self):
        if self.tile_index is None:
            index_file = os.path.join(self.base_dir, 'index.yaml')
            bbox = (-180, -90, 180, 90)
            self.tile_index = index.create(index_file, bbox, _parse_srtm_tile,
                                           self)

        return self.tile_index

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

        tile_index = self._ensure_tile_index()

        for t in index.intersections(tile_index, tile_bbox):
            tiles.add(t)

        return tiles

    def vrts_for(self, tile):
        """
        Returns a list of sets of tiles, with each list element intended as a
        separate VRT for use in GDAL.

        The reason for this is that GDAL doesn't do any compositing _within_
        a single VRT, so if there are multiple overlapping source rasters in
        the VRT, only one will be chosen. This isn't often the case - most
        raster datasets are non-overlapping apart from deliberately duplicated
        margins.
        """
        return [self.downloads_for(tile)]

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

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
