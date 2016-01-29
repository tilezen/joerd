import unittest
import joerd.source.ned as ned


class TestNEDSource(unittest.TestCase):

    def test_zip_file_name_parsing(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.zip'
        bbox = ned._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_img_file_name_parsing(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.img'
        bbox = ned._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)
