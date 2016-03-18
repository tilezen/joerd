from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.mask as mask
from joerd.mkdir_p import mkdir_p
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
        self.url = parent.url
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
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

    def urls(self):
        dir = "%s%03d" % ("E" if self.x >= 0 else "W", abs(self.x))
        res = self._res()
        dname = "/%(res)sdarcsec/mea/%(dir)s/" % dict(res=res, dir=dir)
        return [self.url + dname + self._file_name()]

    def verifier(self):
        return check.is_gdal

    def options(self):
        return self.download_options

    def output_file(self):
        fname = self._file_name()
        return os.path.join(self.base_dir, fname)

    def unpack(self, store, tmp):
        with store.upload_dir() as target:
            mkdir_p(os.path.join(target, self.base_dir))
            output_file = os.path.join(target, self.output_file())
            mask.negative(tmp.name, "GTiff", output_file)

    def freeze_dry(self):
        return dict(type='gmted', x=self.x, y=self.y)


class GMTED(object):

    def __init__(self, options={}):
        self.num_download_threads = options.get('num_download_threads')
        self.base_dir = options.get('base_dir', 'gmted')
        self.url = options['url']
        self.xs = options['xs']
        self.ys = options['ys']
        self.download_options = options

    def get_index(self):
        # GMTED is a static set of files - there's no need for an index, but we
        # do need a directory to store stuff in.
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

    def existing_files(self):
        for base, dirs, files in os.walk(self.base_dir):
            for f in  files:
                if f.endswith('tif'):
                    yield os.path.join(base, f)

    def rehydrate(self, data):
        assert data.get('type') == 'gmted', \
            "Unable to rehydrate %r from GMTED." % data
        return GMTEDTile(self, data['x'], data['y'])

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

    def srs(self):
        return srs.wgs84()

    def filter_type(self, src_res, dst_res):
        # seems like GRA_Lanczos has trouble with nodata, which is causing
        # "ringing" near the edges of the data.
        return gdal.GRA_Bilinear if src_res > dst_res else gdal.GRA_Cubic

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
