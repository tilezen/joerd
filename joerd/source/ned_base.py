from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.index as index
import joerd.mask as mask
import joerd.tmpdir as tmpdir
from multiprocessing import Pool
from contextlib import closing
from shutil import copyfile
from ftplib import FTP
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
import urllib2
import shutil
import yaml
import time
import math
from itertools import groupby


class NEDTile(object):
    def __init__(self, parent, state_code, region_name, year, bbox):
        self.ftp_server = parent.ftp_server
        self.base_path = parent.base_path
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
        self.is_topobathy = parent.is_topobathy
        self.state_code = state_code
        self.region_name = region_name
        self.year = int(year)
        self.bbox = bbox

    def __key(self):
        return (self.state_code, self.region_name, self.year, self.bbox)

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.__key() == b.__key()

    def __hash__(self):
        return hash(self.__key())

    def urls(self):
        return ['ftp://%s/%s/%s' % (self.ftp_server,
                                    self.base_path,
                                    self.zip_name())]

    def verifier(self):
        return check.is_zip

    def options(self):
        return self.download_options

    def output_file(self):
        return os.path.join(self.base_dir, self.img_name())

    def unpack(self, tmp):
        img = self.img_name()

        if self.is_topobathy:
            with zipfile.ZipFile(tmp.name, 'r') as zfile:
                zfile.extract(img, self.base_dir)
                zfile.extract(img + ".aux.xml", self.base_dir)

        else:
            with tmpdir.tmpdir() as d:
                with zipfile.ZipFile(tmp.name, 'r') as zfile:
                    zfile.extract(img, d)
                    zfile.extract(img + ".aux.xml", self.base_dir)

                mask.negative(os.path.join(d, img),
                              "HFA", self.output_file())

    def base_name(self):
        def fmt(v, neg, pos):
            return (pos if v >= 0 else neg,
                    abs(int(v)),
                    abs(int(round(100 * math.modf(v)[0]))))

        return "ned19_%s%02dx%02d_%s%03dx%02d_%s_%s_%4d" \
            % (fmt(self.bbox.bounds[3], 's', 'n') +
               fmt(self.bbox.bounds[0], 'w', 'e') +
               (self.state_code, self.region_name, self.year))

    def img_name(self):
        return self.base_name() + ".img"

    def zip_name(self):
        return self.base_name() + ".zip"


UNIVERSAL_NED_PATTERN = re.compile(
    '^ned19_'
    '([ns])([0-9]{2})x([0257][05])_' # northing
    '([ew])([0-9]{3})x([0257][05])_' # easting
    '([a-z]{2})_' # two letter state code
    '([a-z0-9_]+)_' # the name of the region
    '(20[0-9]{2})' # the year of the data
    '\.zip')


def _parse_ned_tile(fname, parent):
    m = UNIVERSAL_NED_PATTERN.match(fname)

    if not m:
        return None

    y = int(m.group(2)) + float(m.group(3)) / 100.0
    x = int(m.group(5)) + float(m.group(6)) / 100.0
    if m.group(1) == 's':
        y = -y
    if m.group(4) == 'w':
        x = -x
    bbox = BoundingBox(x, y - 0.25, x + 0.25, y)

    state_code = m.group(7)
    region_name = m.group(8)
    year = int(m.group(9))

    return NEDTile(parent, state_code, region_name, year, bbox)


class NEDBase(object):

    def __init__(self, is_topobathy, options={}):
        self.num_download_threads = options.get('num_download_threads')
        self.base_dir = options['base_dir']
        self.ftp_server = options['ftp_server']
        self.base_path = options['base_path']
        self.pattern = re.compile(options['pattern'])
        self.download_options = download.options(options)
        self.tile_index = None
        self.is_topobathy = is_topobathy

    def get_index(self):
        index_file = os.path.join(self.base_dir, 'index.yaml')
        # if index doesn't exist, or is more than 24h old
        if not os.path.isfile(index_file) or \
           time.time() > os.path.getmtime(index_file) + 86400:
            self.download_index(index_file)

    def download_index(self, index_file):
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        logger = logging.getLogger('ned')
        logger.info('Fetching NED index...')

        files = []
        for zname in self._list_ned_files():
            files.append(zname)

        with open(index_file, 'w') as f:
            f.write(yaml.dump(files))

    def _ensure_tile_index(self):
        if self.tile_index is None:
            index_file = os.path.join(self.base_dir, 'index.yaml')
            bbox = (-180, -90, 180, 90)
            self.tile_index = index.create(index_file, bbox, _parse_ned_tile,
                                           self)

        return self.tile_index

    def existing_files(self):
        for base, dirs, files in os.walk(self.base_dir):
            for f in files:
                if f.endswith('img'):
                    yield os.path.join(base, f)

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the NED scale, then there's no
        # point in including NED, it'll be far too fine to make a difference.
        # NED is 1/9th arc second.
        if tile.max_resolution() > 20 * 1.0 / (3600 * 9):
            return tiles

        # buffer by 0.0025 degrees (81px) to grab neighbouring tiles and ensure
        # some overlap to take care of boundary issues.
        tile_bbox = tile.latlon_bbox().buffer(0.0025)

        tile_index = self._ensure_tile_index()

        for t in index.intersections(tile_index, tile_bbox):
            if self.pattern.match(t.zip_name()):
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

        NED is one of those datasets for which there are overlapping regions.
        The state/region name and bbox are independent, so we choose to order
        them alphabetically, for want of a better way.

        Note that it appears the years in NED are non-overlapping.
        """
        vrts = []
        tiles = self.downloads_for(tile)

        def keyfunc(tile):
            return (tile.state_code, tile.region_name)

        for k, ts in groupby(sorted(tiles, key=keyfunc), keyfunc):
            vrts.append(set(ts))

        return vrts

    def _list_ned_files(self):
        ftp = FTP(self.ftp_server)
        files = []

        def _callback(zname):
            t = _parse_ned_tile(zname, self)
            if t is not None:
                files.append(t.zip_name())

        ftp.login()
        ftp.cwd(self.base_path)
        try:
            ftp.set_pasv(True)
            ftp.retrlines('NLST', _callback)
            ftp.quit()
        except EOFError:
            pass

        return files

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

    def srs(self):
        return srs.wgs84()

    def _ned_parse_filename(self, fname):
        t = _parse_ned_tile(fname, self)
        if t is None:
            return None

        if self.pattern.match(t.zip_name()):
            return t.bbox

        return None
