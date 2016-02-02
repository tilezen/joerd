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
import numpy


HALF_ARC_SEC = (1.0/3600.0)*.5
TILE_NAME_PATTERN = re.compile('^([0-9]+)/([0-9]+)/([0-9]+)$')


def _tile_name(z, x, y):
    return '%d/%d/%d' % (z, x, y)


def _parse_tile(tile_name):
    m = TILE_NAME_PATTERN.match(tile_name)
    if m:
        z = int(m.group(1))
        x = int(m.group(2))
        y = int(m.group(3))
        return (z, x, y)
    return None


MERCATOR_WORLD_SIZE = 40075016.68


def _tx_bbox(tx, bbox, expand=0.0):
    xs = []
    ys = []
    for i in range(0,4):
        ix = float(bbox[i & 2])
        iy = float(bbox[(i & 1) * 2 + 1])
        x, y, z = tx.TransformPoint(ix, iy)
        xs.append(x)
        ys.append(y)
    bbox = (min(xs), min(ys), max(xs), max(ys))
    xspan = bbox[2] - bbox[0]
    yspan = bbox[3] - bbox[1]
    return (bbox[0] - 0.5 * expand * xspan,
            bbox[1] - 0.5 * expand * yspan,
            bbox[2] + 0.5 * expand * xspan,
            bbox[3] + 0.5 * expand * yspan)


def _merc_bbox(z, x, y):
    extent = float(1 << z)
    return BoundingBox(
        MERCATOR_WORLD_SIZE * (x / extent - 0.5),
        MERCATOR_WORLD_SIZE * (0.5 - (y + 1) / extent),
        MERCATOR_WORLD_SIZE * ((x + 1) / extent - 0.5),
        MERCATOR_WORLD_SIZE * (0.5 - y / extent))

def _latlon_bbox(z, x, y):
    merc = _merc_bbox(z, x, y)

    merc_srs = osr.SpatialReference()
    merc_srs.ImportFromEPSG(3857)
    latlon_srs = osr.SpatialReference()
    latlon_srs.ImportFromEPSG(4326)

    tx = osr.CoordinateTransformation(merc_srs, latlon_srs)

    return BoundingBox(*_tx_bbox(tx, merc.bounds))

def _lonlat_to_xy(zoom, lon, lat):
    merc_srs = osr.SpatialReference()
    merc_srs.ImportFromEPSG(3857)
    latlon_srs = osr.SpatialReference()
    latlon_srs.ImportFromEPSG(4326)

    tx = osr.CoordinateTransformation(latlon_srs, merc_srs)

    x, y, z = tx.TransformPoint(float(lon), float(lat))

    extent = 1 << zoom
    tx = int(extent * ((x / MERCATOR_WORLD_SIZE) + 0.5))
    ty = int(extent * (0.5 - (y / MERCATOR_WORLD_SIZE)))
    return (tx, ty)


class Terrarium:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'terrarium_tiles')
        self.zooms = options.get('zooms', [13])
        self.enable_browser_png = options.get('enable_browser_png', False)

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox):
                return True
        return False

    def generate_tiles(self):
        logger = logging.getLogger('terrarium')
        tiles = set()

        for zoom in self.zooms:
            for r in self.regions:
                lx, ly = _lonlat_to_xy(zoom, r.bounds[0], r.bounds[3])
                ux, uy = _lonlat_to_xy(zoom, r.bounds[2], r.bounds[1])

                for x in range(lx, ux + 1):
                    for y in range(ly, uy + 1):
                        tiles.add(_tile_name(zoom, x, y))

        logger.info("Generated %d tile jobs." % len(tiles))
        return list(tiles)

    def process_tile(self, tile):
        logger = logging.getLogger('terrarium')

        t = _parse_tile(tile)
        if t is None:
            raise Exception("Unable to parse %r as terrarium tile name."
                            % tile)

        logger.debug("Generating tile %r..." % tile)
        z, x, y = t
        bbox = _merc_bbox(z, x, y)

        mid_dir = os.path.join(self.output_dir, str(z), str(x))
        if not os.path.isdir(mid_dir):
            try:
                os.makedirs(mid_dir)
            except OSError as e:
                # swallow the error if the directory exists - it's
                # probably another thread creating it.
                if e.errno != errno.EEXIST or not os.path.isdir(mid_dir):
                    raise

        tile_file = os.path.join(self.output_dir, tile + ".tif")

        outfile = tile_file
        dst_bbox = bbox.bounds
        dst_x_size = 256
        dst_y_size = 256

        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(3857)

        dst_drv = gdal.GetDriverByName("GTiff")
        dst_ds = dst_drv.Create(outfile, dst_x_size, dst_y_size, 1, gdal.GDT_Int16)
        dst_x_res = float(dst_bbox[2] - dst_bbox[0]) / dst_x_size
        dst_y_res = float(dst_bbox[3] - dst_bbox[1]) / dst_y_size
        dst_gt = (dst_bbox[0], dst_x_res, 0,
                  dst_bbox[3], 0, -dst_y_res)
        dst_ds.SetGeoTransform(dst_gt)
        dst_ds.SetProjection(dst_srs.ExportToWkt())
        dst_ds.GetRasterBand(1).SetNoDataValue(-32768)

        # figure out what the approximate scale of the output image is in
        # lat/lon coordinates. this is used to select the appropriate filter.
        ll_bbox = _latlon_bbox(z, x, y)
        ll_x_res = float(ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_y_res = float(ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size

        composite.compose(self.sources, dst_ds, dst_bbox, logger,
                          min(ll_x_res, ll_y_res))

        mem_drv = gdal.GetDriverByName("MEM")
        mem_ds = mem_drv.Create('', dst_x_size, dst_y_size, 1, gdal.GDT_UInt16)
        mem_ds.SetGeoTransform(dst_gt)
        mem_ds.SetProjection(dst_srs.ExportToWkt())
        mem_ds.GetRasterBand(1).SetNoDataValue(0)

        # convert from int16 to uint16 by shifting everything +32768. note that
        # the conversion relies on uint16's wrap-around overflow behaviour.
        # see this for more information:
        # http://stackoverflow.com/questions/7715406/how-can-i-efficiently-transform-a-numpy-int8-array-in-place-to-a-value-shifted-n
        pixels = dst_ds.GetRasterBand(1).ReadAsArray(0, 0, dst_x_size, dst_y_size)
        pixels = pixels.view(numpy.uint16)
        pixels += 32768
        res = mem_ds.GetRasterBand(1).WriteArray(pixels)

        png_file = os.path.join(self.output_dir, tile + ".png")
        png_drv = gdal.GetDriverByName("PNG")
        png_ds = png_drv.CreateCopy(png_file, mem_ds)

        # "browser" PNG is an image which will display okay in the browser. this
        # can be very useful for demos, or checking that the data is looking
        # okay. it's perhaps less useful for "production" use, so is disabled by
        # default.
        if self.enable_browser_png:
            pixels = (numpy.clip(pixels, 31768, 34317) - 31768) / 10
            mem2_ds = mem_drv.Create('', dst_x_size, dst_y_size, 1, gdal.GDT_Byte)
            mem2_ds.SetGeoTransform(dst_gt)
            mem2_ds.SetProjection(dst_srs.ExportToWkt())
            mem2_ds.GetRasterBand(1).SetNoDataValue(0)
            mem2_ds.GetRasterBand(1).WriteArray(pixels)
            png2_file = os.path.join(self.output_dir, tile + ".u8.png")
            png2_ds = png_drv.CreateCopy(png2_file, mem2_ds)

            del mem2_ds
            del png2_ds

        del dst_ds
        del mem_ds
        del png_ds

        assert os.path.isfile(tile_file)

        logger.info("Done generating tile %r" % tile_file)


def create(regions, sources, options):
    return Terrarium(regions, sources, options)
