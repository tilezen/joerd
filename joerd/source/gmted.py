from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
from multiprocessing import Pool
from contextlib import closing
from shutil import copyfileobj
import os.path
import os
import requests
import logging
import re
import tempfile
import sys
import traceback
import subprocess
import glob
from osgeo import gdal


class GMTEDTile(object):
    def __init__(self, parent, x, y):
        self.parent = parent
        self.x = x
        self.y = y

    def __key(self):
        return (self.x, self.y)

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.__key() == b.__key()

    def __hash__(self):
        return hash(self.__key())

    def _res(self):
        return '300' if self.y == -90 else '075'

    def _file_name(self):
        res = self._res()
        xname = "%03d%s" % (abs(self.x), "E" if self.x >= 0 else "W")
        yname = "%02d%s" % (abs(self.y), "N" if self.y >= 0 else "S")
        return "%(y)s%(x)s_20101117_gmted_mea%(res)s.tif" % \
            dict(res=res, x=xname, y=yname)

    def url(self):
        dir = "%s%03d" % ("E" if self.x >= 0 else "W", abs(self.x))
        res = self._res()
        dname = "/%(res)sdarcsec/mea/%(dir)s/" % dict(res=res, dir=dir)
        return self.parent.url + dname + self._file_name()

    def verifier(self):
        return check.is_gdal

    def options(self):
        return self.parent.download_options

    def output_file(self):
        fname = self._file_name()
        return os.path.join(self.parent.base_dir, fname)

    def unpack(self, tmp):
        with open(self.output_file(), 'w') as out:
            copyfileobj(tmp, out)


class GMTED(object):

    def __init__(self, options={}):
        self.num_download_threads = options.get('num_download_threads')
        self.base_dir = options.get('base_dir', 'gmted')
        self.url = options['url']
        self.xs = options['xs']
        self.ys = options['ys']
        self.download_options = download.options(options)

    def get_index(self):
        # GMTED is a static set of files - there's no need for an index, but we
        # do need a directory to store stuff in.
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the GMTED scale, then there's no
        # point in including GMTED, it'll be far too fine to make a difference.
        # GMTED is 7.5 arc seconds at best (30 at the poles).
        if tile.max_resolution() > 20 * 7.5 / 3600:
            return tiles

        # buffer by 0.1 degrees (48px) to grab neighbouring tiles to ensure
        # that there's no tile edge artefacts.
        tile_bbox = tile.latlon_bbox().buffer(0.1)

        for y in self.ys:
            for x in self.xs:
                bbox = BoundingBox(x, y, x + 30, y + 20)
                if tile_bbox.intersects(bbox):
                    tiles.add(GMTEDTile(self, x, y))

        return tiles

    def srs(self):
        return srs.wgs84()

    def mask_negative(self):
        return True

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

    def _parse_bbox(self, ns_deg, is_ns, ew_deg, is_ew, res):
        bottom = int(ns_deg)
        left = int(ew_deg)

        if is_ns == 'S':
            bottom = -bottom
        if is_ew == 'W':
            left = -left

        b = BoundingBox(left, bottom, left + 30, bottom + 20)
        return b


def create(options):
    return GMTED(options)
