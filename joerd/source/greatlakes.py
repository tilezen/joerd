from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.mask as mask
import joerd.tmpdir as tmpdir
from joerd.mkdir_p import mkdir_p
from shutil import copyfileobj
import os.path
import os
import logging
from osgeo import gdal
import tarfile


# hard-coded bounding boxes for each of the Great Lake datasets. this is because
# there's no link between the name of each piece of data and its bounding box,
# which was a design flaw / assumption for other data sources.
#
# also, we store the vertical offset of the dataset datum which doesn't appear
# to be part of the dataset itself. the vertical datums were obtained from
# https://tidesandcurrents.noaa.gov/gldatums.html
#
GREAT_LAKES = {
    'erie': {
        'bbox': BoundingBox(-84.0004167, 41.0004166, -78.0004166, 43.0004167),
        'datum': 173.5
    },
    'huron': {
        'bbox': BoundingBox(-84.5004167, 43.0004166, -79.6837500, 46.5004167),
        'datum': 176.0
    },
    'michigan': {
        'bbox': BoundingBox(-88.0004167, 41.6237499, -84.5004166, 46.0904167),
        'datum': 176.0
    },
    'ontario': {
        'bbox': BoundingBox(-79.9004167, 43.1504166, -76.0504166, 44.2504167),
        'datum': 74.2
    },
    'superior': {
        'bbox': BoundingBox(-92.2004167, 46.0004166, -84.0004166, 49.5004167),
        'datum': 183.2
    }
}


# base URL of dataset
BASE_URL = 'https://www.ngdc.noaa.gov/mgg/greatlakes'


class GreatLake(object):
    def __init__(self, parent, lake):
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
        self.lake = lake

    def __key(self):
        return self.lake

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.lake == b.lake

    def __hash__(self):
        return hash(self.__key())

    def urls(self):
        return [ \
            "%(base_url)s/%(lake)s/data/geotiff/%(lake)s_lld.geotiff.tar.gz" \
            % dict(base_url=BASE_URL,lake=self.lake) ]

    def verifier(self):
        return check.is_tar_gz

    def options(self):
        return self.download_options

    def output_file(self):
        fname = self.lake + ".tif"
        return os.path.join(self.base_dir, fname)

    def unpack(self, store, tmp):
        # the file inside the TAR is named like this - we're only interested
        # in the GeoTIFF file, as it already contains all the information
        # that we need.
        tif_file = "%(lake)s_lld/%(lake)s_lld.tif" % dict(lake=self.lake)
        shift = GREAT_LAKES[self.lake]['datum']

        with tmpdir.tmpdir() as tmp_dir:
            with tarfile.open(tmp.name, mode='r:gz') as tar:
                tar.extract(tif_file, tmp_dir)

            tif_path = os.path.join(tmp_dir, tif_file)
            assert os.path.exists(tif_path), "Didn't extract TIF"

            with store.upload_dir() as target:
                mkdir_p(os.path.join(target, self.base_dir))
                output_file = os.path.join(target, self.output_file())

                mask.datum_shift(tif_path, 'GTiff', output_file, shift)

    def freeze_dry(self):
        return dict(type='greatlakes', lake=self.lake)


class GreatLakes(object):

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'greatlakes')
        self.download_options = options

    def get_index(self):
        # Great Lakes is a static set of files - there's no need for an index,
        # but we do need a directory to store stuff in.
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

    def existing_files(self):
        for base, dirs, files in os.walk(self.base_dir):
            for f in files:
                if f.endswith('tif'):
                    yield os.path.join(base, f)

    def rehydrate(self, data):
        assert data.get('type') == 'greatlakes', \
            "Unable to rehydrate %r from Great Lakes." % data
        return GreatLake(self, data['lake'])

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the original scale, then
        # there's no point in including it, as it'll be far too fine to make
        # a difference. Great Lakes data is 3 arc seconds.
        if tile.max_resolution() > 20 * 3.0 / 3600:
            return tiles

        # buffer by 0.1 degrees (48px) to grab neighbouring tiles to ensure
        # that there's no tile edge artefacts.
        tile_bbox = tile.latlon_bbox().buffer(0.1)

        for lake, info in GREAT_LAKES.items():
            if tile_bbox.intersects(info['bbox']):
                tiles.add(GreatLake(self, lake))

        return tiles

    def vrts_for(self, tile):
        """
        Returns a list of sets of GreatLakes, with each list element intended
        as a separate VRT for use in GDAL.

        The reason for this is that GDAL doesn't do any compositing _within_
        a single VRT, so if there are multiple overlapping source rasters in
        the VRT, only one will be chosen. This isn't often the case - most
        raster datasets are non-overlapping apart from deliberately duplicated
        margins.
        """
        return [self.downloads_for(tile)]

    def srs(self):
        return srs.nad83()

    def filter_type(self, src_res, dst_res):
        # seems like GRA_Lanczos has trouble with nodata, which is causing
        # "ringing" near the edges of the data.
        return gdal.GRA_Bilinear if src_res > dst_res else gdal.GRA_Cubic


def create(options):
    return GreatLakes(options)
