import unittest
import joerd.output.skadi as skadi


class TestTileName(unittest.TestCase):

    def test_tile_name_parsing(self):
        for x in range(0, 360):
            for y in range(0, 180):
                tile_name = skadi._tile_name(x, y)
                self.assertEqual((x, y), skadi._parse_tile(tile_name))
