import unittest
import joerd.output.terrarium as terrarium


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
