from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.index as index
import joerd.mask as mask
import joerd.tmpdir as tmpdir
from joerd.mkdir_p import mkdir_p
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


class NED13Tile(object):
    def __init__(self, parent, fname, lon, lat):
        self.ftp_server = parent.ftp_server
        self.base_path = parent.base_path
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
        self.fname = fname
        assert self.fname.endswith('.zip')
        self.lon = lon
        self.lat = lat

        self.bbox = BoundingBox(self.lon, self.lat - 1,
                                self.lon + 1, self.lat)

    def freeze_dry(self):
        return dict(type='ned13', fname=self.fname,
                    lon=self.lon, lat=self.lat)

    def __key(self):
        return (self.lon, self.lat)

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

    def unpack(self, store, tmp):
        img = self.img_name()

        with store.upload_dir() as target:
            target_dir = os.path.join(target, self.base_dir)
            mkdir_p(target_dir)

            with tmpdir.tmpdir() as d:
                with zipfile.ZipFile(tmp.name, 'r') as zfile:
                    zfile.extract(img, d)

                output_file = os.path.join(target, self.output_file())
                mask.negative(os.path.join(d, img), "HFA", output_file)

    def img_name(self):
        base_name = self.fname.replace('.zip', '')

        if base_name.startswith('USGS_NED_13_'):
            return base_name + ".img"
        else:
            return 'img' + base_name + '_13.img'

    def zip_name(self):
        return self.fname


UNIVERSAL_NED_PATTERN = re.compile(
    '^(USGS_NED_13_)?' # optional prefix
    '([ns])([0-9]{2})' # northing
    '([ew])([0-9]{3})' # easting
    '(_IMG)?' # optional suffix
    '\.zip')


def _parse_ned_tile(fname, parent):
    m = UNIVERSAL_NED_PATTERN.match(fname)

    if not m:
        return None

    y = int(m.group(3))
    x = int(m.group(5))
    if m.group(2) == 's':
        y = -y
    if m.group(4) == 'w':
        x = -x

    return NED13Tile(parent, fname, x, y)


class NED13(object):

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'ned13')
        self.ftp_server = options['ftp_server']
        self.base_path = options['base_path']
        self.download_options = options
        self.tile_index = None

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
        logger.info('Fetching NED13 index...')

        files = []
        for zname in self._uniq_ned_files(self._list_ned_files()):
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

    def rehydrate(self, data):
        assert data.get('type') == 'ned13', \
            "Unable to rehydrate %r in NED13." % data
        return NED13Tile(self, data['fname'], data['lon'], data['lat'])

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the NED scale, then there's no
        # point in including NED, it'll be far too fine to make a difference.
        # NED13 is 1/3rd arc second.
        if tile.max_resolution() > 20 * 1.0 / (3600 * 3):
            return tiles

        # buffer by 0.0075 degrees (81px) to grab neighbouring tiles and ensure
        # some overlap to take care of boundary issues.
        tile_bbox = tile.latlon_bbox().buffer(0.0075)

        tile_index = self._ensure_tile_index()

        for t in index.intersections(tile_index, tile_bbox):
            tiles.add(t)

        return tiles

    def vrts_for(self, tile):
        """
        Returns a list of sets of tiles, with each list element intended as a
        separate VRT for use in GDAL.

        NED13 is non-overlapping.
        """
        return [self.downloads_for(tile)]

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

    def _uniq_ned_files(self, files):
        # make a second pass over the data to prefer more recent files which
        # have names like USGS_NED_13_*
        old_files = set()
        new_files = set()

        for f in files:
            if f.startswith('USGS_NED_13_'):
                new_files.add(f)
            else:
                old_files.add(f)

        # remove any old files equivalent to the new name
        for f in new_files:
            old_name = f.replace('USGS_NED_13_','').replace('_IMG', '')
            old_files.discard(old_name)

        return list(new_files) + list(old_files)

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

    def srs(self):
        return srs.wgs84()

    def _ned_parse_filename(self, fname):
        t = _parse_ned_tile(fname, self)
        if t is None:
            return None

        return t.bbox


def create(options):
    return NED13(options)
