from joerd.util import BoundingBox
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


HALF_ARC_SEC = (1.0/3600.0)*.5
TILE_NAME_PATTERN = re.compile('^([NS])([0-9]{2})([EW])([0-9]{3})$')


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


class Skadi:

    def __init__(self, regions, sources, output_dir='tiles'):
        self.regions = regions
        self.sources = sources
        self.output_dir = output_dir

    def _bbox(self, x, y):
        return BoundingBox(
            (x - 180) - HALF_ARC_SEC,
            (y - 90) - HALF_ARC_SEC,
            (x - 179) + HALF_ARC_SEC,
            (y - 89) + HALF_ARC_SEC)

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox):
                return True
        return False

    def generate_tiles(self):
        logger = logging.getLogger('skadi')
        tiles = []

        for x in range(0, 360):
            for y in range(0, 180):
                bbox = self._bbox(x, y)
                if self._intersects(bbox):
                    tiles.append(_tile_name(x, y))

        logger.info("Generated %d tile jobs." % len(tiles))
        return tiles

    def process_tile(self, tile):
        logger = logging.getLogger('skadi')

        t = _parse_tile(tile)
        if t is None:
            raise Exception("Unable to parse %r as skadi tile name."
                            % tile)

        logger.info("Generating tile %r..." % tile)
        x, y = t
        bbox = self._bbox(x, y)

        mid_dir = os.path.join(self.output_dir,
                               ("N" if y >= 0 else "S") + ("%02d" % abs(y)))
        if not os.path.isdir(mid_dir):
            try:
                os.makedirs(mid_dir)
            except OSError as e:
                # swallow the error if the directory exists - it's
                # probably another thread creating it.
                if e.errno != errno.EEXIST or not os.path.isdir(mid_dir):
                    raise

        tile_file = os.path.join(mid_dir, tile + ".hgt")

        outfile = tile_file
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

        composite.compose(self.sources, dst_ds, dst_bbox, logger)

        logger.info("Writing SRTMHGT: %r" % outfile)
        srtm_drv = gdal.GetDriverByName("SRTMHGT")
        srtm_ds = srtm_drv.CreateCopy(outfile, dst_ds)

        del dst_ds
        del srtm_ds

        assert os.path.isfile(tile_file)

        logger.info("Done generating tile %r" % tile_file)


def create(regions, sources):
    return Skadi(regions, sources)
