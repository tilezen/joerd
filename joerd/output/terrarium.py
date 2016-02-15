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


class TerrariumTile:
    def __init__(self, parent, z, x, y):
        self.parent = parent
        self.z = z
        self.x = x
        self.y = y

    def set_sources(self, sources):
        logger = logging.getLogger('terrarium')
        logger.debug("Set sources on tile z=%r: %r"
                     % (self.z, [type(s).__name__ for s in sources]))
        self.sources = sources

    def latlon_bbox(self):
        return self.parent.latlon_bbox(self.z, self.x, self.y)

    def max_resolution(self):
        bbox = self.latlon_bbox().bounds
        return max((bbox[2] - bbox[0]) / 256.0,
                   (bbox[3] - bbox[1]) / 256.0)

    def render(self):
        logger = logging.getLogger('terrarium')

        bbox = _merc_bbox(self.z, self.x, self.y)

        mid_dir = os.path.join(self.parent.output_dir, str(self.z), str(self.x))
        if not os.path.isdir(mid_dir):
            try:
                os.makedirs(mid_dir)
            except OSError as e:
                # swallow the error if the directory exists - it's
                # probably another thread creating it.
                if e.errno != errno.EEXIST or not os.path.isdir(mid_dir):
                    raise

        tile = _tile_name(self.z, self.x, self.y)
        tile_file = os.path.join(self.parent.output_dir, tile + ".tif")
        logger.debug("Generating tile %r..." % tile_file)

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
        ll_bbox = self.parent.latlon_bbox(self.z, self.x, self.y)
        ll_x_res = float(ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_y_res = float(ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size

        composite.compose(self, dst_ds, logger, min(ll_x_res, ll_y_res))

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

        png_file = os.path.join(self.parent.output_dir, tile + ".png")
        png_drv = gdal.GetDriverByName("PNG")
        png_ds = png_drv.CreateCopy(png_file, mem_ds)

        # "browser" PNG is an image which will display okay in the browser. this
        # can be very useful for demos, or checking that the data is looking
        # okay. it's perhaps less useful for "production" use, so is disabled by
        # default.
        if self.parent.enable_browser_png:
            pixels = (numpy.clip(pixels, 31768, 34317) - 31768) / 10
            mem2_ds = mem_drv.Create('', dst_x_size, dst_y_size, 1, gdal.GDT_Byte)
            mem2_ds.SetGeoTransform(dst_gt)
            mem2_ds.SetProjection(dst_srs.ExportToWkt())
            mem2_ds.GetRasterBand(1).SetNoDataValue(0)
            mem2_ds.GetRasterBand(1).WriteArray(pixels)
            png2_file = os.path.join(self.parent.output_dir, tile + ".u8.png")
            png2_ds = png_drv.CreateCopy(png2_file, mem2_ds)

            del mem2_ds
            del png2_ds

        del dst_ds
        del mem_ds
        del png_ds

        assert os.path.isfile(tile_file)

        source_names = [type(s).__name__ for s in self.sources]
        logger.info("Done generating tile %r from %s"
                    % (tile_file, ", ".join(source_names)))


class Terrarium:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'terrarium_tiles')
        self.zooms = options.get('zooms', [13])
        self.enable_browser_png = options.get('enable_browser_png', False)
        self._setup_transforms()

    def _setup_transforms(self):
        # cache these transforms, as they are mildly expensive to create and
        # are used a lot when intersecting mercator tiles against latlon
        # sources.
        self.merc_srs = osr.SpatialReference()
        self.merc_srs.ImportFromEPSG(3857)
        self.latlon_srs = osr.SpatialReference()
        self.latlon_srs.ImportFromEPSG(4326)

        self.tx = osr.CoordinateTransformation(self.merc_srs, self.latlon_srs)
        self.tx_inv = osr.CoordinateTransformation(self.latlon_srs,
                                                   self.merc_srs)

    # The Terrarium object is pickled to send it to other processes when we
    # generate tiles in parallel, but the OSR / GDAL objects can't be pickled.
    # So we must exclude them from the pickling process and regenerate them
    # at the other side.
    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['merc_srs']
        del odict['latlon_srs']
        del odict['tx']
        del odict['tx_inv']
        return odict

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._setup_transforms()

    def generate_tiles(self):
        logger = logging.getLogger('terrarium')
        tiles = set()

        for zoom in self.zooms:
            for r in self.regions:
                lx, ly = self.lonlat_to_xy(zoom, r.bounds[0], r.bounds[3])
                ux, uy = self.lonlat_to_xy(zoom, r.bounds[2], r.bounds[1])

                for x in range(lx, ux + 1):
                    for y in range(ly, uy + 1):
                        tiles.add(TerrariumTile(self, zoom, x, y))

        logger.info("Generated %d tile jobs." % len(tiles))
        return list(tiles)

    def latlon_bbox(self, z, x, y):
        merc = _merc_bbox(z, x, y)

        return BoundingBox(*_tx_bbox(self.tx, merc.bounds))

    def lonlat_to_xy(self, zoom, lon, lat):
        x, y, z = self.tx_inv.TransformPoint(float(lon), float(lat))

        extent = 1 << zoom
        tx = int(extent * ((x / MERCATOR_WORLD_SIZE) + 0.5))
        ty = int(extent * (0.5 - (y / MERCATOR_WORLD_SIZE)))
        return (tx, ty)


def create(regions, sources, options):
    return Terrarium(regions, sources, options)
