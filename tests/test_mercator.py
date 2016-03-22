import unittest
from joerd.mercator import Mercator


class TestMercator(unittest.TestCase):

    def test_lonlat_to_xy(self):
        m = Mercator()

        for zoom in range(0, 20):
            cmax = (1 << zoom) - 1
            self.assertEqual(m.lonlat_to_xy(zoom, -180, 90), (0, 0))
            self.assertEqual(m.lonlat_to_xy(zoom, 180, -90), (cmax, cmax))
