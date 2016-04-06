import unittest
import joerd.output.terrarium as terrarium
from joerd.region import Region
from joerd.util import BoundingBox


class TestTerrariumTiles(unittest.TestCase):

    def test_location_to_xy(self):
        t = terrarium.Terrarium([], [])
        x, y = t.mercator.lonlat_to_xy(19, -122.39199, 37.79123)
        self.assertEqual(83897, x)
        self.assertEqual(202618, y)

    def test_projections(self):
        t = terrarium.Terrarium([], [])
        z, x, y = (13, 1308, 3165)
        ll_bbox = t.mercator.latlon_bbox(z, x, y)
        cx = 0.5 * (ll_bbox.bounds[0] + ll_bbox.bounds[2])
        cy = 0.5 * (ll_bbox.bounds[1] + ll_bbox.bounds[3])
        self.assertEqual((x, y), t.mercator.lonlat_to_xy(z, cx, cy))

    def test_generate_tiles(self):
        regions = [
            Region(BoundingBox(-124.56, 32.4, -114.15, 42.03), [8, 10])
        ]
        t = terrarium.Terrarium(regions, [])
        expected = set([
            (8, 41, 99),
            (8, 43, 98)
        ])
        for tile in t.generate_tiles():
            coord = (tile.z, tile.x, tile.y)
            if coord in expected:
                expected.remove(coord)
        self.assertEqual(expected, set([]))
