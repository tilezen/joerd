from joerd.util import BoundingBox
from joerd.region import RegionTile
from tempfile import NamedTemporaryFile as Tmp
from osgeo import osr, gdal
import re
import logging
import os
import os.path
import tempfile
import subprocess
import shutil
import errno
import sys
import joerd.composite as composite
import gzip
import math


HALF_ARC_SEC = (1.0/3600.0)*.5
TILE_NAME_PATTERN = re.compile('^([NS])([0-9]{2})([EW])([0-9]{3})$')


# Skadi tiles are at 1 arc second = 1,296,000 pixels around the circumference
# of the whole world. This is about equivalent to a zoom of 12.3
SKADI_NOMINAL_ZOOM = 12.3


def _bbox(x, y):
    return BoundingBox(
        (x - 180) - HALF_ARC_SEC,
        (y - 90) - HALF_ARC_SEC,
        (x - 179) + HALF_ARC_SEC,
        (y - 89) + HALF_ARC_SEC)


def _tile_name(x, y):
    return '%s%02d%s%03d' % \
        ('S' if y < 90 else 'N', abs(y - 90),
         'W' if x < 180 else 'E', abs(x - 180))


def _parse_tile(tile_name):
    m = TILE_NAME_PATTERN.match(tile_name)
    if m:
        y = int(m.group(2))
        x = int(m.group(4))
        if m.group(1) == 'S':
            y = -y
        if m.group(3) == 'W':
            x = -x
        return (x + 180, y + 90)
    return None


class SkadiTile(object):
    def __init__(self, output_dir, x, y):
        self.output_dir = output_dir
        self.x = x
        self.y = y

    def set_sources(self, sources):
        logger = logging.getLogger('skadi')
        logger.debug("Set sources on tile (x,y)=%r: %r"
                     % ((self.x, self.y), [type(s).__name__ for s in sources]))
        self.sources = sources

    def freeze_dry(self):
        return dict(type='skadi', x=self.x, y=self.y)

    def latlon_bbox(self):
        return _bbox(self.x, self.y)

    def max_resolution(self):
        return 1.0 / 3600;

    def render(self, tmp_dir):
        logger = logging.getLogger('skadi')

        bbox = _bbox(self.x, self.y)

        mid_dir = os.path.join(tmp_dir, self.output_dir,
                               ("N" if self.y >= 90 else "S") +
                               ("%02d" % abs(self.y - 90)))
        if not os.path.isdir(mid_dir):
            try:
                os.makedirs(mid_dir)
            except OSError as e:
                # swallow the error if the directory exists - it's
                # probably another thread creating it.
                if e.errno != errno.EEXIST or not os.path.isdir(mid_dir):
                    raise

        tile = _tile_name(self.x, self.y)
        hgt_file = os.path.join(mid_dir, tile + ".hgt")
        tile_file = os.path.join(mid_dir, tile + ".hgt.gz")
        logger.info("Generating tile %r..." % tile)

        dst_bbox = bbox.bounds
        dst_x_size = 3601
        dst_y_size = 3601

        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(4326)

        # for SRTM, must first buffer in memory, then write to disk with
        # CreateCopy.
        dst_drv = gdal.GetDriverByName("MEM")
        dst_ds = dst_drv.Create('', dst_x_size, dst_y_size, 1, gdal.GDT_Int16)
        dst_x_res = float(dst_bbox[2] - dst_bbox[0]) / dst_x_size
        dst_y_res = float(dst_bbox[3] - dst_bbox[1]) / dst_y_size
        dst_gt = (dst_bbox[0], dst_x_res, 0,
                  dst_bbox[3], 0, -dst_y_res)
        dst_ds.SetGeoTransform(dst_gt)
        dst_ds.SetProjection(dst_srs.ExportToWkt())
        dst_ds.GetRasterBand(1).SetNoDataValue(-32768)

        composite.compose(self, dst_ds, logger, min(dst_x_res, dst_y_res))

        logger.debug("Writing SRTMHGT: %r" % hgt_file)
        srtm_drv = gdal.GetDriverByName("SRTMHGT")
        srtm_ds = srtm_drv.CreateCopy(hgt_file, dst_ds)

        del dst_ds
        del srtm_ds

        logger.debug("Compressing HGT -> GZ: %r" % tile_file)
        with gzip.open(tile_file, 'wb') as gz, open(hgt_file, 'rb') as hgt:
            shutil.copyfileobj(hgt, gz)

        os.remove(hgt_file)
        assert os.path.isfile(tile_file)

        logger.info("Done generating tile %r" % tile)


class Skadi:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'tiles')

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox, SKADI_NOMINAL_ZOOM):
                return True
        return False

    def expand_tile(self, bbox, zoom_range):
        tiles = []

        if SKADI_NOMINAL_ZOOM >= zoom_range[0] and \
           SKADI_NOMINAL_ZOOM < zoom_range[1]:
            # Skadi tiles are the same size as SRTM tiles - just a little bit
            # bigger than 1x1 degree.
            xmin, ymin, xmax, ymax = bbox
            xmin = math.floor(xmin) - HALF_ARC_SEC
            ymin = math.floor(ymin) - HALF_ARC_SEC
            xmax = math.ceil(xmax) + HALF_ARC_SEC
            ymax = math.ceil(ymax) + HALF_ARC_SEC
            res = 1.0 / 3600

            # Skadi tiles are only at one resolution, so only return one tile
            tiles.append(RegionTile((xmin, ymin, xmax, ymax), res))

        return tiles

    def generate_tiles(self):
        logger = logging.getLogger('skadi')
        tiles = []

        for x in range(0, 360):
            for y in range(0, 180):
                bbox = _bbox(x, y)
                if self._intersects(bbox):
                    tiles.append(SkadiTile(self.output_dir, x, y))

        logger.info("Generated %d tile jobs." % len(tiles))
        return tiles

    def rehydrate(self, data):
        typ = data.get('type')
        assert typ == 'skadi', "Unable to rehydrate tile of type %r in " \
            "skadi output. Job was: %r" % (typ, data)

        x = data['x']
        y = data['y']
        return SkadiTile(self.output_dir, x, y)


def create(regions, sources, options):
    return Skadi(regions, sources, options)
