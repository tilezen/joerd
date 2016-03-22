from joerd.util import BoundingBox
import joerd.composite as composite
from contextlib2 import contextmanager
from osgeo import osr, gdal
import math


# first tried using the minimum value for this, but it doesn't seem to stay
# stable, and the slightest change is enough to make it != nodata, which sets
# it to "some" data.
# so now using a nice "round" number, which should be less prone to precision
# truncation issues (since all the precision bits are zero).
FLT_NODATA = -3.0e38


MERCATOR_WORLD_SIZE = 40075016.68


def _tile_name(z, x, y):
    return '%d/%d/%d' % (z, x, y)


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


class MercatorTile(object):
    def __init__(self, z, x, y, size, ll_bbox, merc_bbox):
        self.z = z
        self.x = x
        self.y = y
        self.size = size
        self._latlon_bbox = ll_bbox
        self._mercator_bbox = merc_bbox

    def set_sources(self, sources):
        self.sources = sources

    def latlon_bbox(self):
        return self._latlon_bbox

    def max_resolution(self):
        bbox = self.latlon_bbox().bounds
        return max((bbox[2] - bbox[0]) / self.size,
                   (bbox[3] - bbox[1]) / self.size)

    def tile_name(self):
        return _tile_name(self.z, self.x, self.y)

    @contextmanager
    def get_datasource(self, logger):
        bbox = self._mercator_bbox

        dst_bbox = bbox.bounds
        dst_x_size = self.size
        dst_y_size = self.size

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
        ll_bbox = self.latlon_bbox()
        ll_x_res = float(ll_bbox.bounds[2] - ll_bbox.bounds[0]) / dst_x_size
        ll_y_res = float(ll_bbox.bounds[3] - ll_bbox.bounds[1]) / dst_y_size

        composite.compose(self, dst_ds, logger, min(ll_x_res, ll_y_res))

        try:
            yield dst_ds

        finally:
            del dst_ds


class Mercator(object):
    def __init__(self):
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

    # The spatial reference and transform objects are handles to C objects
    # and can't be serialized. However, this object is stateless, and an
    # identical copy can be recreated from scratch without parameters. So
    # that's what happens in __setstate__.
    def __getstate__(self):
        return {}

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._setup_transforms()

    def latlon_bbox(self, z, x, y):
        merc = _merc_bbox(z, x, y)

        return BoundingBox(*_tx_bbox(self.tx, merc.bounds))

    def lonlat_to_xy(self, zoom, lon, lat):
        # clip lat to +/- 85.051129 because that's all that spherical mercator
        # can support. otherwise we get "tolerance condition error".
        lat = min(max(lat, -85.051129), 85.051129)

        x, y, z = self.tx_inv.TransformPoint(float(lon), float(lat))

        extent = 1 << zoom
        tx = int(math.floor(extent * ((x / MERCATOR_WORLD_SIZE) + 0.5)))
        ty = int(math.floor(extent * (0.5 - (y / MERCATOR_WORLD_SIZE))))

        # and clip the result to lie in the allowable domain 0 <= coord < extent
        tx = min(max(0, tx), extent - 1)
        ty = min(max(0, ty), extent - 1)

        return (tx, ty)

    def mercator_bbox(self, z, x, y):
        return _merc_bbox(z, x, y)
