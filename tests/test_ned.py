import unittest
import joerd.source.ned as ned
import joerd.source.ned_base as ned_base
import joerd.source.ned_topobathy as ned_topo


FAKE_OPTIONS = dict(
    ftp_server='',
    base_path=''
)


class TestNEDSource(unittest.TestCase):

    def test_zip_file_name_parsing_topo(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.zip'
        n = ned_topo.create(FAKE_OPTIONS)
        bbox = n.base._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_zip_file_name_parsing_normal_topo_2(self):
        fname = 'ned19_n38x00_w122x50_tx_cameronco06_cameronco_2003.zip'
        n = ned_topo.create(FAKE_OPTIONS)
        bbox = n.base._ned_parse_filename(fname)
        self.assertTrue(bbox is None)

    def test_zip_file_name_parsing_normal(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_2010.zip'
        n = ned.create(FAKE_OPTIONS)
        bbox = n.base._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_zip_file_name_parsing_normal_2(self):
        fname = 'ned19_n38x00_w122x50_tx_cameronco06_cameronco_2003.zip'
        n = ned.create(FAKE_OPTIONS)
        bbox = n.base._ned_parse_filename(fname)
        self.assertTrue(bbox is not None)
        self.assertEqual((-122.5, 37.75, -122.25, 38.0), bbox.bounds)

    def test_none_file_name_parsing_normal(self):
        fname = 'ned19_n38x00_w122x50_ca_sanfrancisco_topobathy_2010.img'
        n = ned.create(FAKE_OPTIONS)
        bbox = n.base._ned_parse_filename(fname)
        self.assertTrue(bbox is None)

    def test_roundtrip_name(self):
        for fname in [
                'ned19_n45x50_w097x75_sd_marshallco_2010.zip',
                'ned19_n47x25_w097x50_nd_redriver_g_2008.zip',
                'ned19_n47x25_w068x75_me_aroostook_2012.zip',
                'ned19_n40x50_w098x50_ne_rainwater_2009.zip',
                'ned19_n39x50_w095x25_ks_leavenworth_2010.zip',
                'ned19_n43x50_w070x75_me_cumberlandcoast_2006.zip',
                'ned19_n35x50_w096x75_ok_potawatomie_2011.zip',
                'ned19_n46x00_w120x25_or_wa_id_columbiariver_2010.zip',
                'ned19_n38x00_w122x25_ca_sanfrancisocoast_2010.zip',
                'ned19_n38x00_w076x25_md_somersetwicomicocos_2012.zip',
                'ned19_n41x00_w084x50_oh_north_2006.zip',
                'ned19_n43x00_w095x75_ia_northwest_2008.zip',
                'ned19_n47x00_w122x00_wa_lewis_2009.zip',
                'ned19_n31x25_w091x75_la_statewide_2006.zip',
                'ned19_n43x75_w092x25_mn_9southeastcounties_2008.zip',
                'ned19_n40x25_w080x25_pa_southwest_2006.zip',
                'ned19_n60x50_w150x25_ak_kenaicnt_10ft_2008.zip',
                'ned19_n35x75_w077x75_nc_statewide_2003.zip',
                'ned19_n34x75_w083x75_ga_lanierlake_2010.zip',
                'ned19_n30x75_w082x25_ga_warecharltonco_2010.zip',
                'ned19_n28x75_w081x00_fl_volusiaco_2006.zip',
                'ned19_n32x50_w093x25_la_statewide_2006.zip',
                'ned19_n33x00_w084x25_ga_potatocreek_2009.zip',
                'ned19_n39x25_w086x50_in_bartholomew_jacksoncos_2011.zip',
                'ned19_n30x00_w082x00_fl_clayputnam_2007.zip',
                'ned19_n38x00_w112x75_ut_cedarvalley_2011.zip',
                'ned19_n30x00_w082x75_fl_suwanneeriver_7a4_2013.zip',
                'ned19_n39x25_w096x50_ks_gearyco_2010.zip',
                'ned19_n42x25_w096x00_ia_south_westcentral_2008.zip',
                'ned19_n43x00_w083x50_mi_oaklandco_2008.zip',
        ]:
            t = ned_base._parse_ned_tile(fname, None)
            self.assertTrue(t is not None, fname)
            f = t.zip_name()
            self.assertEqual(fname, f)
