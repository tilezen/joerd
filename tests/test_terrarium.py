import unittest
import joerd.output.terrarium as terrarium


class TestTerrariumTiles(unittest.TestCase):

    def test_tile_name_parsing(self):
        for z in range(8, 12):
            for x in range(0, 64):
                for y in range(0, 64):
                    tile_name = terrarium._tile_name(z, x, y)
                    self.assertEqual((z, x, y),
                        terrarium._parse_tile(tile_name))

    def test_location_to_xy(self):
        x, y = terrarium._lonlat_to_xy(19, -122.39199, 37.79123)
        self.assertEqual(83897, x)
        self.assertEqual(202618, y)

    def test_projections(self):
        z, x, y = (13, 1308, 3165)
        ll_bbox = terrarium._latlon_bbox(z, x, y)
        cx = 0.5 * (ll_bbox.bounds[0] + ll_bbox.bounds[2])
        cy = 0.5 * (ll_bbox.bounds[1] + ll_bbox.bounds[3])
        self.assertEqual((x, y), terrarium._lonlat_to_xy(z, cx, cy))
