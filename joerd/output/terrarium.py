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
# first tried using the minimum value for this, but it doesn't seem to stay
# stable, and the slightest change is enough to make it != nodata, which sets
# it to "some" data.
# so now using a nice "round" number, which should be less prone to precision
# truncation issues (since all the precision bits are zero).
FLT_NODATA = -3.0e38


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


class TerrariumTile(object):
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

    def render(self, tmp_dir):
        logger = logging.getLogger('terrarium')

        bbox = _merc_bbox(self.z, self.x, self.y)

        mid_dir = os.path.join(tmp_dir, self.parent.output_dir,
                               str(self.z), str(self.x))
        if not os.path.isdir(mid_dir):
            try:
                os.makedirs(mid_dir)
            except OSError as e:
                # swallow the error if the directory exists - it's
                # probably another thread creating it.
                if e.errno != errno.EEXIST or not os.path.isdir(mid_dir):
                    raise

        tile = _tile_name(self.z, self.x, self.y)
        logger.debug("Generating tile %r..." % tile)

        dst_bbox = bbox.bounds
        dst_x_size = 256
        dst_y_size = 256

        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(3857)

        dst_drv = gdal.GetDriverByName("MEM")
        dst_ds = dst_drv.Create('', dst_x_size, dst_y_size, 1, gdal.GDT_Float32)

        dst_x_res = float(dst_bbox[2] - dst_bbox[0]) / dst_x_size
        dst_y_res = float(dst_bbox[3] - dst_bbox[1]) / dst_y_size
        dst_gt = (dst_bbox[0], dst_x_res, 0,
                  dst_bbox[3], 0, -dst_y_res)
        dst_ds.SetGeoTransform(dst_gt)
        dst_ds.SetProjection(dst_srs.ExportToWkt())
        dst_ds.GetRasterBand(1).SetNoDataValue(FLT_NODATA)

        # figure out what the approximate scale of the output image is in
        # lat/lon coordinates. this is used to select the appropriate filter.
        ll_bbox = self.parent.latlon_bbox(self.z, self.x, self.y)
        ll_x_res = float(ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_y_res = float(ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size

        composite.compose(self, dst_ds, logger, min(ll_x_res, ll_y_res))

        if self.parent.enable_png:
            # we want the output to be 3-channels R, G, B with:
            #   uheight = height + 32768.0
            #   R = int(height) / 256
            #   G = int(height) % 256
            #   B = int(frac(height) * 256)
            # Looks like gdal doesn't handle "nodata" across multiple channels,
            # so we'll use R=0, which corresponds to height < 32,513 which is
            # lower than any depth on Earth, so we should be okay.
            mem_drv = gdal.GetDriverByName("MEM")
            mem_ds = mem_drv.Create('', dst_x_size, dst_y_size, 3, gdal.GDT_Byte)
            mem_ds.SetGeoTransform(dst_gt)
            mem_ds.SetProjection(dst_srs.ExportToWkt())
            mem_ds.GetRasterBand(1).SetNoDataValue(0)

            pixels = dst_ds.GetRasterBand(1).ReadAsArray(0, 0, dst_x_size, dst_y_size)
            # transform to uheight, clamping the range
            pixels += 32768.0
            numpy.clip(pixels, 0.0, 65535.0, out=pixels)

            r = (pixels / 256).astype(numpy.uint8)
            res = mem_ds.GetRasterBand(1).WriteArray(r)
            assert res == gdal.CPLE_None

            g = (pixels % 256).astype(numpy.uint8)
            res = mem_ds.GetRasterBand(2).WriteArray(g)
            assert res == gdal.CPLE_None

            b = ((pixels * 256) % 256).astype(numpy.uint8)
            res = mem_ds.GetRasterBand(3).WriteArray(b)
            assert res == gdal.CPLE_None

            png_file = os.path.join(tmp_dir, self.parent.output_dir,
                                    tile + ".png")
            png_drv = gdal.GetDriverByName("PNG")
            png_ds = png_drv.CreateCopy(png_file, mem_ds)

            # explicitly delete the datasources. the Python-GDAL docs suggest
            # that this is a good idea not only to dispose of memory buffers
            # but also to ensure that the backing file handles are closed.
            del mem_ds
            del png_ds

            assert os.path.isfile(png_file)

        if self.parent.enable_tif:
            # TIFF compresses best if we stick to integer pixels, using LZW
            # and the "2" type predictor. we might be able to keep some bits
            # of precision with float32 and DISCARD_LSB, but that's only
            # available in GDAL >= 2.0
            tile_file = os.path.join(tmp_dir, self.parent.output_dir,
                                     tile + ".tif")
            outfile = tile_file
            tif_drv = gdal.GetDriverByName("GTiff")
            tif_ds = tif_drv.Create(outfile, dst_x_size, dst_y_size, 1,
                                    gdal.GDT_Int16, options = [
                                        'COMPRESS=LZW',
                                        'PREDICTOR=2'
                                    ])
            tif_ds.SetGeoTransform(dst_gt)
            tif_ds.SetProjection(dst_srs.ExportToWkt())
            tif_ds.GetRasterBand(1).SetNoDataValue(-32768)

            pixels = dst_ds.GetRasterBand(1).ReadAsArray(0, 0, dst_x_size, dst_y_size)
            # transform to integer height, clamping the range
            numpy.clip(pixels, -32768, 32767, out=pixels)
            tif_ds.GetRasterBand(1).WriteArray(pixels.astype(numpy.int16))

            # explicitly delete the datasources. the Python-GDAL docs suggest that
            # this is a good idea not only to dispose of memory buffers but also
            # to ensure that the backing file handles are closed.
            del tif_ds

            assert os.path.isfile(tile_file)

        del dst_ds

        source_names = [type(s).__name__ for s in self.sources]
        logger.info("Done generating tile %r from %s"
                    % (tile, ", ".join(source_names)))


class Terrarium:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'terrarium_tiles')
        self.enable_png = options.get('enable_png', True)
        self.enable_tif = options.get('enable_tif', True)
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

        for r in self.regions:
            rbox = r.bbox.bounds
            for zoom in range(*r.zoom_range):
                lx, ly = self.lonlat_to_xy(zoom, rbox[0], rbox[3])
                ux, uy = self.lonlat_to_xy(zoom, rbox[2], rbox[1])

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
