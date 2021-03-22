from bs4 import BeautifulSoup
from joerd.util import BoundingBox
import joerd.download as download
import joerd.check as check
import joerd.srs as srs
import joerd.index as index
import joerd.mask as mask
import joerd.tmpdir as tmpdir
from joerd.mkdir_p import mkdir_p
from contextlib2 import closing, ExitStack
from shutil import copyfile, move
import os.path
import os
import io
import requests
import logging
import re
import tempfile
import sys
import zipfile
import traceback
import subprocess
import glob
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import yaml
import time
import subprocess
import mimetypes
from itertools import groupby

class DMR1Tile(object):
    def __init__(self, parent, tile, name, block, bbox):
        self.uri = parent.uri
        self.download_options = parent.download_options
        self.base_dir = parent.base_dir
        self.name = name
        self.block = block
        self.tile = tile
        self.bbox = bbox
        self.region_bbox = parent.region_bbox

    def __key(self):
        return self.name

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.__key() == b.__key()

    def __hash__(self):
        return hash(self.__key())

    def urls(self):
        uri_list = ["%(uri)s/b_%(block)s/D96TM/TM1_%(name)s.txt" % dict(uri=self.uri,block=self.block,name=self.name)]
        return uri_list

    def verifier(self):
        return is_txt

    def options(self):
        return self.download_options

    def output_file(self):
        file_name = "TM1_" + self.name + ".tif"
        return os.path.join(self.base_dir, file_name)

    def _tif_file(self):
        # returns the name of the geotiff file within the distributed archive.
        return "TM1_%(name)s.tif" % dict(name=self.name)

    def unpack(self, store, txt_file):

        with store.upload_dir() as target:
            target_dir = os.path.join(target, self.base_dir)
            mkdir_p(target_dir)
            with tmpdir.tmpdir() as temp_dir:
                tif_file = os.path.join(temp_dir, self._tif_file())

                xyz_file = os.path.join(temp_dir, "TM1_%(name)s.xyz" % dict(name=self.name))

                #Flip x any y, as they are fliped in dmr1
                data = []
                with open(txt_file.name, 'r') as dmr_file:
                    for l in dmr_file:
                        data.append(l.strip().split(";"))

                data = sorted(data, key = lambda x: (float(x[1]), float(x[0])))

                xyzlist = []
                for l in data:
                    xyzlist.append('{x};{y};{z}\n'.format(x=l[0],y=l[1],z=l[2]))
                with open(xyz_file, 'w') as xyz:
                    xyz.writelines(xyzlist)

                #Correct NS (North South) resolution and convert to xyz to tif
                ds = gdal.Open(xyz_file)
                ds = gdal.Warp(tif_file,ds,format="GTiff",dstSRS="EPSG:3794") 
                ds = None

                #subprocess.check_output("sort -k2 -n -t';' -k1 {tfile} -o {ofile}".format(tfile=txt_file.name, ofile=xyz_file), cwd=temp_dir, shell=True)
                #subprocess.check_output("gdalwarp -t_srs EPSG:3794 -ts -overwrite {xfile} {tfile}".format(xfile=xyz_file,tfile=tif_file), cwd=temp_dir, shell=True)

                #Move the file to the store
                output_file = os.path.join(target, self.output_file())
                move(tif_file, output_file)
                

    def freeze_dry(self):
        return dict(type='dmr1', tile=self.tile)

#IS_DMR1_FILE = re.compile('^b_([0-9]{2})/D96TM/TM1_([0-9]{2,3})_([0-9]{2,3}).txt')
IS_DMR1_FILE = re.compile(r'^b_([0-9]{2})\|TM1_([0-9]{2,3})_([0-9]{2,3})\|([\d*\.?\d*]+)\|([\d*\.?\d*]+)\|([\d*\.?\d*]+)\|([\d*\.?\d*]+)')

def is_txt(self):
    def func(tmp):
        if mimetypes.guess_type(tmp.name)[0] == 'text/plain':
            return True
        else:
            return False    
    return func
    

def _parse_dmr1_tile(tile, parent):
    m = IS_DMR1_FILE.match(tile)

    if not m:
        return None

    d96_left = float(m.group(4))
    d96_bottom = float(m.group(5))
    d96_right = float(m.group(6))
    d96_top = float(m.group(7))

    block = int(m.group(1))
    name = "%(x)s_%(y)s" % dict(x=str(m.group(2)),y=str(m.group(3)))

    #D96/TM (EPSG::3794) to WGS84 (EPSG::4326)
    src = osr.SpatialReference()
    tgt = osr.SpatialReference()
    src.ImportFromEPSG(3794)
    tgt.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(src, tgt)
    coords = transform.TransformPoint(d96_left, d96_bottom)
    left,bottom = coords[0:2]
    coords = transform.TransformPoint(d96_right, d96_top)
    right,top= coords[0:2]

    bbox = BoundingBox(left, bottom, right, top)

    #This is so the memory doesn't overflow, due to the big size of the index
    #and is to be removed on a production server
    if bbox.intersects(parent.region_bbox):
        return DMR1Tile(parent, tile, name, block, bbox)

    return None

class DMR1(object):
    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'dmr1')
        self.uri = options['uri']
        self.fishnet_url = options['fishnet_url']
        box = options['bbox']
        self.region_bbox = BoundingBox(box['left'], box['bottom'], box['right'],box['top'])
        self.download_options = options
        self.tile_index = None

    def get_index(self):
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)
        index_name = 'index.yaml'
        index_file = os.path.join(self.base_dir, index_name)
        # if index doesn't exist, or is more than 24h old
        if not os.path.isfile(index_file) or \
            time.time() > os.path.getmtime(index_file) + 86400:
                self.download_index(index_file)

    def download_index(self, index_file):
        logger = logging.getLogger('dmr1')
        logger.info('Fetcthing D96TM index...')

        """
        fishnet = 'LIDAR_FISHNET_D96.shp'

        #these tiles do not have dmr1
        blacklist = ['b_21/D96TM/TM1_393_35.txt',
        'b_21/D96TM/TM1_392_35.txt', 
        'b_23/D96TM/TM1_509_169.txt'
        'b_24/D96TM/TM1_616_148.txt',
        'b_24/D96TM/TM1_617_148.txt',
        'b_24/D96TM/TM1_618_148.txt',
        'b_24/D96TM/TM1_622_147.txt',
        'b_24/D96TM/TM1_622_148.txt',
        'b_24/D96TM/TM1_623_148.txt',
        'b_24/D96TM/TM1_623_149.txt']

        req = requests.get(self.fishnet_url, stream=True)
        with tmpdir.tmpdir() as d:
            with zipfile.ZipFile(io.BytesIO(req.content)) as zip_file:
                    zip_file.extractall(d)

            fishnet_file = os.path.join(d, fishnet)
            driver = ogr.GetDriverByName("ESRI Shapefile")
            dataSource = driver.Open(fishnet_file, 1)
            layer = dataSource.GetLayer()

            for feature in layer:
                link = feature.GetField("BLOK") + "/D96TM/TM1_" + feature.GetField("NAME") + ".txt";
                if link not in blacklist:
                    links.append(link)
            layer.ResetReading()
        """
        req = requests.get(self.fishnet_url, allow_redirects=True)

        with open(index_file, 'w') as file:
            file.write(req.content)
        #file.write(yaml.dump(whitelist))

    def _ensure_tile_index(self):
        if self.tile_index is None:
            index_file = os.path.join(self.base_dir, 'index.yaml')

            bbox = (13.39027778,45.40750000,16.62694444,46.88333333)
            self.tile_index = index.create(index_file, bbox, _parse_dmr1_tile, self)

        return self.tile_index

    def existing_files(self):
        for base, dirs, files in os.walk(self.base_dir):
            for f in  files:
                if f.endswith('tif'):
                    yield os.path.join(base, f)

    def rehydrate(self, data):
        assert data.get('type') == 'dmr1', \
            "Unable to rehydrate %r from Slovenia." %data
        return _parse_dmr1_tile(data['tile'], self)

    def downloads_for(self, tile):
        tiles = set()
        # if the tile scale is greater than 20x the D96TM scale, then there's no
        # point in including D96TM, it'll be far too fine to make a difference.
        # D96TM is 1m (Aboue same as 1/9th arc second).

        if tile.max_resolution() > 20 * 1.0 / (3600 * 9):
            return tiles

        # buffer by 0.0075 degrees (81px) to grab neighbouring tiles and ensure
        # some overlap to take care of boundary issues.
        tile_bbox = tile.latlon_bbox().buffer(0.0075)

        tile_index = self._ensure_tile_index()

        for t in index.intersections(tile_index, tile_bbox):
                    tiles.add(t)

        return tiles

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos if src_res > dst_res else gdal.GRA_Cubic

    def vrts_for(self, tile):
        """
        Returns a list of sets of tiles, with each list element intended as a
        separate VRT for use in GDAL.
        
        D96TM is overlapping.
        """
        vrt = []
        tiles =  self.downloads_for(tile)

        def func(tile):
            return (tile.tile)

        for k, t in groupby(sorted(tiles, key=func), func):
            vrt.append(set(t))

        return vrt

    def srs(self):
        return srs.d96()

def create(options):
    return DMR1(options)