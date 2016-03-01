import unittest
import joerd.source.srtm as srtm


FAKE_OPTIONS = dict(
    url='',
)


class TestSRTMSource(unittest.TestCase):

    def test_file_name_parsing_1(self):
        fname = 'N37W123.SRTMGL1.hgt.zip'
        s = srtm.create(FAKE_OPTIONS)
        bbox = s._parse_bbox(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-123, 37, -122, 38), bbox.bounds)

    def test_file_name_parsing_2(self):
        fname = 'N38W122.SRTMGL1.hgt.zip'
        s = srtm.create(FAKE_OPTIONS)
        bbox = s._parse_bbox(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122, 38, -121, 39), bbox.bounds)

    def test_file_name_parsing_3(self):
        fname = 'N37W116.SRTMSWBD.raw.zip'
        s = srtm.create(FAKE_OPTIONS)
        bbox = s._parse_bbox(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-116, 37, -115, 38), bbox.bounds)
