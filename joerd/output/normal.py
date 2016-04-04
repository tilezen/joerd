from joerd.util import BoundingBox
from joerd.region import RegionTile
from joerd.mkdir_p import mkdir_p
from osgeo import osr, gdal
import logging
import os
import os.path
import errno
import sys
import joerd.composite as composite
import joerd.mercator as mercator
import numpy
import math
from geographiclib.geodesic import Geodesic
import bisect


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


class NormalTile(mercator.MercatorTile):
    def __init__(self, parent, z, x, y):
        super(NormalTile, self).__init__(
            z, x, y, 256,
            parent.mercator.latlon_bbox(z, x, y),
            parent.mercator.mercator_bbox(z, x, y))
        self.output_dir = parent.output_dir

    def freeze_dry(self):
        return dict(type='normal', z=self.z, x=self.x, y=self.y)

    def render(self, tmp_dir):
        logger = logging.getLogger('normal')

        bbox = self._mercator_bbox

        mid_dir = os.path.join(tmp_dir, self.output_dir,
                               str(self.z), str(self.x))
        mkdir_p(mid_dir)

        tile = self.tile_name()
        tile_file = os.path.join(tmp_dir, self.output_dir,
                                 tile + ".png")
        logger.debug("Generating tile %r..." % tile)

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
        if mid_min_x < -0.5 * mercator.MERCATOR_WORLD_SIZE:
            filter_lft_margin = 0
            mid_min_x = dst_bbox[0]
        if mid_min_y < -0.5 * mercator.MERCATOR_WORLD_SIZE:
            filter_bot_margin = 0
            mid_min_y = dst_bbox[1]
        if mid_max_x > 0.5 * mercator.MERCATOR_WORLD_SIZE:
            filter_rgt_margin = 0
            mid_max_x = dst_bbox[2]
        if mid_max_y > 0.5 * mercator.MERCATOR_WORLD_SIZE:
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
        mid_ds.GetRasterBand(1).SetNoDataValue(mercator.FLT_NODATA)

        # figure out what the approximate scale of the output image is in
        # lat/lon coordinates. this is used to select the appropriate filter.
        ll_bbox = self._latlon_bbox
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

        # first, we normalise to unit vectors. this puts each element of img
        # in the range (-1, 1). the "einsum" stuff is serious black magic, but
        # what it (should be) saying is "for each i,j in the rows and columns,
        # the output is the sum of img[i,j,k]*img[i,j,k]" - i.e: the square.
        norm = numpy.sqrt(numpy.einsum('ijk,ijk->ij', img, img))

        # the norm is now the "wrong shape" according to numpy, so we need to
        # copy the norm value out into RGB components.
        norm_copy = norm[:, :, numpy.newaxis]

        # dividing the img by norm_copy should give us RGB components with
        # values between -1 and 1, but we need values between 0 and 255 for
        # PNG channels. so we move and scale the values to fit in that range.
        scaled = (128.0 * (img / norm_copy + 1.0))

        # and finally clip it to (0, 255) just in case
        img = numpy.clip(scaled, 0.0, 255.0)

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
        ext = img[filter_top_margin:(filter_top_margin+dst_y_size), \
                  filter_lft_margin:(filter_lft_margin+dst_x_size)]
        dst_ds.GetRasterBand(1).WriteArray(ext[...,0].astype(numpy.uint8))
        dst_ds.GetRasterBand(2).WriteArray(ext[...,1].astype(numpy.uint8))
        dst_ds.GetRasterBand(3).WriteArray(ext[...,2].astype(numpy.uint8))

        # add hypsometric tint index as alpha channel
        dst_ds.GetRasterBand(4).WriteArray(
            hyps[filter_top_margin:(filter_top_margin+dst_y_size),
                 filter_lft_margin:(filter_lft_margin+dst_x_size)])

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
                    % (tile, ", ".join(source_names)))


class Normal:

    def __init__(self, regions, sources, options={}):
        self.regions = regions
        self.sources = sources
        self.output_dir = options.get('output_dir', 'normal_tiles')
        self.enable_browser_png = options.get('enable_browser_png', False)
        self.mercator = mercator.Mercator()

    def expand_tile(self, bbox, zoom_range):
        tiles = []

        for z in range(*zoom_range):
            lx, ly = self.mercator.lonlat_to_xy(z, bbox[0], bbox[1])
            ux, uy = self.mercator.lonlat_to_xy(z, bbox[2], bbox[3])
            ll = self.mercator.latlon_bbox(z, lx, ly).bounds
            ur = self.mercator.latlon_bbox(z, ux, uy).bounds
            res = max((ll[2] - ll[0]) / 256.0,
                      (ur[2] - ur[0]) / 256.0)
            tiles.append(RegionTile((ll[0], ll[1], ur[2], ur[3]), res))

        return tiles

    def generate_tiles(self):
        logger = logging.getLogger('normal')
        tiles = set()

        for r in self.regions:
            rbox = r.bbox.bounds
            for zoom in range(*r.zoom_range):
                lx, ly = self.mercator.lonlat_to_xy(zoom, rbox[0], rbox[3])
                ux, uy = self.mercator.lonlat_to_xy(zoom, rbox[2], rbox[1])

                for x in range(lx, ux + 1):
                    for y in range(ly, uy + 1):
                        bbox = self.latlon_bbox(zoom, x, y)
                        tiles.add(NormalTile(self, zoom, x, y))

        logger.info("Generated %d tile jobs." % len(tiles))
        return list(tiles)

    def latlon_bbox(self, z, x, y):
        return self.mercator.latlon_bbox(z, x, y)

    def mercator_bbox(self, z, x, y):
        return self.mercator.mercator_bbox(z, x, y)

    def rehydrate(self, data):
        typ = data.get('type')
        assert typ == 'normal', "Unable to rehydrate tile of type %r in " \
            "normal output. Job was: %r" % (typ, data)

        z = data['z']
        x = data['x']
        y = data['y']
        return NormalTile(self, z, x, y)


def create(regions, sources, options):
    return Normal(regions, sources, options)
