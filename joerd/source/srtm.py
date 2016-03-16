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
    '^([NS])([0-9]{2})([EW])([0-9]{3}).SRTM(?:GL1.hgt|SWBD.raw).zip$')


class SRTMTile(object):
    def __init__(self, parent, link, fname, bbox, is_masked):
        self.url = parent.url
        self.mask_url = parent.mask_url
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
        self.link = link
        self.mask_link = self.link.replace(".SRTMGL1.hgt", ".SRTMSWBD.raw")
        self.is_masked = is_masked
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
        url_list = [self.url + "/" + self.link]
        mask_link = self.link.replace(".SRTMGL1.hgt", ".SRTMSWBD.raw")
        if self.is_masked:
            url_list.append(self.mask_url + "/" + mask_link)
        return url_list

    def verifier(self):
        return check.is_zip

    def options(self):
        return self.download_options

    def output_file(self):
        return os.path.join(self.base_dir, self.fname)

    def unpack(self, data_zip, mask_zip=None):
        # if there's no mask, then just extract the SRTM as-is.
        if mask_zip is None:
            with zipfile.ZipFile(data_zip.name, 'r') as zfile:
                zfile.extract(self.fname, self.base_dir)
            return

        # otherwise, make a temporary directory to keep the SRTM and
        # mask in while compositing them.
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

    def freeze_dry(self):
        return dict(type='srtm', link=self.link, is_masked=self.is_masked)


def _parse_srtm_tile(link, parent, is_masked=None):
    fname = link.replace(".SRTMGL1.hgt.zip", ".hgt")
    bbox = parent._parse_bbox(link)
    if is_masked is None:
        mask_link = link.replace(".SRTMGL1.hgt", ".SRTMSWBD.raw")
        is_masked = parent.is_masked(mask_link)
    return SRTMTile(parent, link, fname, bbox, is_masked)


class SRTM(object):

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'srtm')
        self.url = options['url']
        self.mask_url = options.get('mask-url')
        self.download_options = options
        self.tile_index = None
        self.mask_index = None

    # Pickling the tile index is probably not a good idea, since it is
    # an FFI / C object. Setting it to None should cause it to be
    # regenerated post-unpickle.
    def __getstate__(self):
        odict = self.__dict__.copy()
        odict['tile_index'] = None
        odict['mask_index'] = None
        return odict

    def get_index(self):
        for name in ['tile', 'mask']:
            self.get_one_index(name)

    def get_one_index(self, name):
        fname = 'index_%s.yaml' % name
        index_file = os.path.join(self.base_dir, fname)
        # if index doesn't exist, or is more than 24h old
        if not os.path.isfile(index_file) or \
           time.time() > os.path.getmtime(index_file) + 86400:
            self.download_index(index_file, name)

    def download_index(self, index_file, name):
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        logger = logging.getLogger('srtm')
        logger.info('Fetching SRTM %r index...' % name)

        url = None
        if name == 'tile':
            url = self.url
        if name == 'mask':
            url = self.mask_url

        r = requests.get(url)
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
            index_file = os.path.join(self.base_dir, 'index_tile.yaml')
            bbox = (-180, -90, 180, 90)
            self.tile_index = index.create(index_file, bbox, _parse_srtm_tile,
                                           self)

        return self.tile_index

    def _ensure_mask_index(self):
        if self.mask_index is None:
            index_file = os.path.join(self.base_dir, 'index_mask.yaml')
            self.mask_index = set(yaml.load(open(index_file)))

        return self.mask_index

    def is_masked(self, filename):
        return filename in self._ensure_mask_index()

    def existing_files(self):
        for base, dirs, files in os.walk(self.base_dir):
            for f in  files:
                if f.endswith('hgt'):
                    yield os.path.join(base, f)

    def rehydrate(self, data):
        assert data.get('type') == 'srtm', \
            "Unable to rehydrate %r from SRTM." % data
        return _parse_srtm_tile(data['link'], self, data['is_masked'])

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
