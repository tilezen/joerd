from joerd.util import BoundingBox
from osgeo import osr, gdal
import logging
import os
import os.path
import errno
import sys
import joerd.composite as composite
import numpy
import math
from geographiclib.geodesic import Geodesic
import bisect


# first tried using the minimum value for this, but it doesn't seem to stay
# stable, and the slightest change is enough to make it != nodata, which sets
# it to "some" data.
# so now using a nice "round" number, which should be less prone to precision
# truncation issues (since all the precision bits are zero).
FLT_NODATA = -3.0e38


# Generate a table of heights suitable for use as hypsometric tinting. These
# have only a little precision for bathymetry, and concentrate most of the
# rest in the 0-3000m range, which is where most of the world's population
# lives.
#
# It seemed better to have this as a function which returned the table rather
# than include the table verbatim, as this would be a big blob of unreadable
# numbers.
def _generate_mapping_table():
    table = []
    for i in range(0, 11):
        table.append(-11000 + i * 1000)
    table.append(-100)
    table.append( -50)
    table.append( -20)
    table.append( -10)
    table.append(  -1)
    for i in range(0, 150):
        table.append(20 * i)
    for i in range(0, 60):
        table.append(3000 + 50 * i)
    for i in range(0, 29):
        table.append(6000 + 100 * i)
    return table


# Make a constant version of the table for reference.
HEIGHT_TABLE = _generate_mapping_table()


# Function which returns the index of the maximum height in the height table
# which is lower than the input `h`. I.e: it rounds down. We then _flip_ the
# table "backwards" so that low heights have higher indices. This is so that
# when it's displayed on a regular computer, the lower values near sea level
# have high alpha, making them more opaque.
def _height_mapping_func(h):
    return 255 - bisect.bisect_left(HEIGHT_TABLE, h)


def _tile_name(z, x, y):
    return '%d/%d/%d' % (z, x, y)


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


class NormalTile:
    def __init__(self, parent, z, x, y):
        self.parent = parent
        self.z = z
        self.x = x
        self.y = y

    def set_sources(self, sources):
        logger = logging.getLogger('normal')
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
        logger = logging.getLogger('normal')

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
        tile_file = os.path.join(self.parent.output_dir, tile + ".png")
        logger.debug("Generating tile %r..." % tile_file)

        filter_size = 10

        outfile = tile_file
        dst_bbox = bbox.bounds
        dst_x_size = 256
        dst_y_size = 256
        dst_x_res = float(dst_bbox[2] - dst_bbox[0]) / dst_x_size
        dst_y_res = float(dst_bbox[3] - dst_bbox[1]) / dst_y_size
        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(3857)

        # expand bbox & image to generate "bleed" for image filter
        mid_min_x = dst_bbox[0] - filter_size * dst_x_res
        mid_min_y = dst_bbox[1] - filter_size * dst_y_res
        mid_max_x = dst_bbox[2] + filter_size * dst_x_res
        mid_max_y = dst_bbox[3] + filter_size * dst_y_res
        filter_top_margin = filter_size
        filter_bot_margin = filter_size
        filter_lft_margin = filter_size
        filter_rgt_margin = filter_size

        # clip bounding box back to the edges of the world. GDAL can handle
        # wrapping around the world, but it doesn't give the results that
        # would be expected.
        if mid_min_x < -0.5 * MERCATOR_WORLD_SIZE:
            filter_lft_margin = 0
            mid_min_x = dst_bbox[0]
        if mid_min_y < -0.5 * MERCATOR_WORLD_SIZE:
            filter_bot_margin = 0
            mid_min_y = dst_bbox[1]
        if mid_max_x > 0.5 * MERCATOR_WORLD_SIZE:
            filter_rgt_margin = 0
            mid_max_x = dst_bbox[2]
        if mid_max_y > 0.5 * MERCATOR_WORLD_SIZE:
            filter_top_margin = 0
            mid_max_y = dst_bbox[3]

        mid_x_size = dst_x_size + filter_lft_margin + filter_rgt_margin
        mid_y_size = dst_y_size + filter_bot_margin + filter_top_margin
        mid_bbox = (mid_min_x, mid_min_y, mid_max_x, mid_max_y)

        mid_drv = gdal.GetDriverByName("MEM")
        mid_ds = mid_drv.Create('', mid_x_size, mid_y_size, 1, gdal.GDT_Float32)

        mid_gt = (mid_bbox[0], dst_x_res, 0,
                  mid_bbox[3], 0, -dst_y_res)
        mid_ds.SetGeoTransform(mid_gt)
        mid_ds.SetProjection(dst_srs.ExportToWkt())
        mid_ds.GetRasterBand(1).SetNoDataValue(FLT_NODATA)

        # figure out what the approximate scale of the output image is in
        # lat/lon coordinates. this is used to select the appropriate filter.
        ll_bbox = self.parent.latlon_bbox(self.z, self.x, self.y)
        ll_x_res = float(ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_y_res = float(ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size

        # calculate the resolution of a pixel in real meters for both x and y.
        # this will be used to scale the gradient so that it's consistent
        # across zoom levels.
        ll_mid_x = 0.5 * (ll_bbox.bounds[2] + ll_bbox.bounds[0])
        ll_spc_x = 0.5 * (ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_mid_y = 0.5 * (ll_bbox.bounds[3] + ll_bbox.bounds[1])
        ll_spc_y = 0.5 * (ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size
        geod = Geodesic.WGS84
        # NOTE: in defiance of predictability and regularity, the geod methods
        # take input as (lat, lon) in that order, rather than (x, y) as would
        # be sensible.
        # NOTE: at low zooms, taking the width across the tile starts to break
        # down, so we take the width across a small portion of the interior of
        # the tile instead.
        geodesic_res_x = -1.0 / \
                         geod.Inverse(ll_mid_y, ll_mid_x - ll_spc_x,
                                      ll_mid_y, ll_mid_x + ll_spc_x)['s12']
        geodesic_res_y = 1.0 / \
                         geod.Inverse(ll_mid_y - ll_spc_y, ll_mid_x,
                                      ll_mid_y + ll_spc_y, ll_mid_x)['s12']

        composite.compose(self, mid_ds, logger, min(ll_x_res, ll_y_res))

        pixels = mid_ds.GetRasterBand(1).ReadAsArray(0, 0, mid_x_size, mid_y_size)
        ygrad, xgrad = numpy.gradient(pixels, 2)
        img = numpy.dstack((geodesic_res_x * xgrad, geodesic_res_y * ygrad,
                            numpy.ones((mid_y_size, mid_x_size))))

        def make_normal(v):
            # first, we normalise to unit vectors. this puts each element of v
            # in the range (-1, 1).
            mag = math.sqrt(numpy.dot(v, v))
            # then we squash that into the range (0, 1) and scale it out to
            # (0, 255) for use as a uint8
            v_scaled = 256.0 * 0.5 * (v / mag + 1.0)
            # and finally clip it to (0, 255) just in case
            numpy.clip(v_scaled, 0.0, 255.0, out=v_scaled)
            return v_scaled

        img = numpy.apply_along_axis(make_normal, 2, img)

        # Create output as a 4-channel RGBA image, each (byte) channel
        # corresponds to x, y, z, h where x, y and z are the respective
        # components of the normal, and h is an index into a hypsometric tint
        # table (see HEIGHT_TABLE).
        dst_ds = mid_drv.Create('', dst_x_size, dst_y_size, 4, gdal.GDT_Byte)

        dst_gt = (dst_bbox[0], dst_x_res, 0,
                  dst_bbox[3], 0, -dst_y_res)
        dst_ds.SetGeoTransform(dst_gt)
        dst_ds.SetProjection(dst_srs.ExportToWkt())

        # apply the height mapping function to get the table index.
        func = numpy.vectorize(_height_mapping_func)
        hyps = func(pixels).astype(numpy.uint8)

        # extract the area without the "bleed" margin.
        ext = img[filter_lft_margin:(filter_lft_margin+dst_x_size), \
                  filter_bot_margin:(filter_bot_margin+dst_y_size)]
        dst_ds.GetRasterBand(1).WriteArray(ext[...,0].astype(numpy.uint8))
        dst_ds.GetRasterBand(2).WriteArray(ext[...,1].astype(numpy.uint8))
        dst_ds.GetRasterBand(3).WriteArray(ext[...,2].astype(numpy.uint8))

        # add hypsometric tint index as alpha channel
        dst_ds.GetRasterBand(4).WriteArray(
            hyps[filter_lft_margin:(filter_lft_margin+dst_x_size),
                 filter_bot_margin:(filter_bot_margin+dst_y_size)])

        png_drv = gdal.GetDriverByName("PNG")
        png_ds = png_drv.CreateCopy(tile_file, dst_ds)

        # explicitly delete the datasources. the Python-GDAL docs suggest that
        # this is a good idea not only to dispose of memory buffers but also
        # to ensure that the backing file handles are closed.
        del png_ds
        del dst_ds
        del mid_ds

        assert os.path.isfile(tile_file)

        source_names = [type(s).__name__ for s in self.sources]
        logger.info("Done generating tile %r from %s"
                    % (tile_file, ", ".join(source_names)))


class Normal:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'normal_tiles')
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

    # The Normal object is pickled to send it to other processes when we
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
        logger = logging.getLogger('normal')
        tiles = set()

        for zoom in self.zooms:
            for r in self.regions:
                lx, ly = self.lonlat_to_xy(zoom, r.bounds[0], r.bounds[3])
                ux, uy = self.lonlat_to_xy(zoom, r.bounds[2], r.bounds[1])

                for x in range(lx, ux + 1):
                    for y in range(ly, uy + 1):
                        tiles.add(NormalTile(self, zoom, x, y))

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
    return Normal(regions, sources, options)
