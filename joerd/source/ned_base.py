from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
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


class NEDTile(object):
    def __init__(self, parent, fname, zname, bbox):
        self.parent = parent
        self.img_name = fname
        self.zip_name = zname
        self.bbox = bbox

    def __key(self):
        return (self.img_name, self.zip_name, self.bbox)

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.__key() == b.__key()

    def __hash__(self):
        return hash(self.__key())

    def url(self):
        return 'ftp://%s/%s/%s' % (self.parent.ftp_server,
                                   self.parent.base_path,
                                   self.zip_name)

    def verifier(self):
        return check.is_zip

    def options(self):
        return self.parent.download_options

    def output_file(self):
        return os.path.join(self.parent.base_dir, self.img_name)

    def unpack(self, tmp):
        with zipfile.ZipFile(tmp.name, 'r') as zfile:
            zfile.extract(self.img_name, self.parent.base_dir)
            zfile.extract(self.img_name + ".aux.xml", self.parent.base_dir)


class NEDBase(object):

    def __init__(self, options={}):
        self.num_download_threads = options.get('num_download_threads')
        self.base_dir = options['base_dir']
        self.ftp_server = options['ftp_server']
        self.base_path = options['base_path']
        self.pattern = re.compile(options['pattern'])
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

        logger = logging.getLogger('ned')
        logger.info('Fetching NED index...')

        files = []
        for bbox, fname, zname in self._list_ned_files():
            files.append(dict(fname=fname, zname=zname, bbox=bbox.bounds))

        with open(index_file, 'w') as f:
            f.write(yaml.dump(files))

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

        files = self.index_cache
        if files is None:
            index_file = os.path.join(self.base_dir, 'index.yaml')
            with open(index_file, 'r') as f:
                files = yaml.load(f.read())
            self.index_cache = files

        for f in files:
            bbox = BoundingBox(*f['bbox'])
            if tile_bbox.intersects(bbox) and \
               self.pattern.match(f['fname']):
                tiles.add(NEDTile(self, f['fname'], f['zname'], bbox))

        return tiles

    def _list_ned_files(self):
        ftp = FTP(self.ftp_server)
        files = []

        def _callback(zname):
            bbox = self._ned_parse_filename(zname)
            if bbox is not None:
                fname = zname.replace(".zip", ".img")
                files.append((bbox, fname, zname))

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
        m = self.pattern.match(fname)

        if m:
            y = int(m.group(2)) + float(m.group(3)) / 100.0
            x = int(m.group(5)) + float(m.group(6)) / 100.0
            if m.group(1) == 's':
                y = -y
            if m.group(4) == 'w':
                x = -x
            return BoundingBox(x, y - 0.25, x + 0.25, y)

        return None
