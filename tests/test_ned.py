import unittest
import joerd.source.ned as ned
import joerd.source.ned_topobathy as ned_topo


FAKE_OPTIONS = dict(
    ftp_server='',
    base_path=''
)


class TestNEDSource(unittest.TestCase):

    def test_zip_file_name_parsing_topo(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.zip'
        n = ned_topo.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_img_file_name_parsing_topo(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.img'
        n = ned_topo.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_none_file_name_parsing_topo(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_2010.img'
        n = ned_topo.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is None)

    def test_zip_file_name_parsing_normal(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_2010.zip'
        n = ned.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_img_file_name_parsing_normal(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_2010.img'
        n = ned.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_none_file_name_parsing_normal(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.img'
        n = ned.create([], FAKE_OPTIONS)
        bbox = n._ned_parse_filename(fname)
        self.assertTrue(bbox is None)
