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
import pdal
import yaml
import time
import json
import subprocess

class D96TMTile(object):
	def __init__(self, parent, link, name, block, bbox):
		self.uri = parent.uri
		self.download_options = parent.download_options
		self.base_dir = parent.base_dir
		self.name = name
		self.block = block
		self.link = link
		self.bbox = bbox

	def __key(self):
		return self.name

	def __eq__(a, b):
		return isinstance(b, type(a)) and \
			a.__key() == b.__key()

	def __hash__(self):
		return hash(self.__key())

	def urls(self):
		uri_list = [self.uri + "/" + self.link]
		return uri_list


	def verifier(self):
		return is_las

	def options(self):
		return self.download_options

	def output_file(self):
		file_name = "TMR_" + self.name + ".tif"
		return os.path.join(self.base_dir, file_name)

	def _tif_file(self):
		# returns the name of the geotiff file within the distributed archive.
		return "TMR_%(name)s.tif" % dict(name=self.name)

	def unpack(self, store, las_file):
		tif_file = self._tif_file;

		with store.upload_dir() as target:
			target_dir = os.path.join(target, self.base_dir)
			mkdir_p(target_dir)
			with tmpdir.tmpdir() as temp_dir:

				arr = []
				inp = {
					"type": "readers.las",
					"filename": "%(fname)s" % dict(fname=las_file.name),
					"spatialreference":"EPSG:3794"
				}
				arr.append(inp)
				par = {
					"type": "writers.gdal",
					"resolution": 1,
					"radius": 7,
					"filename": os.path.join(temp_dir, "TMR_%(name)s.tif" % dict(name=self.name))	
				}
				arr.append(par)

				astage = {
					"pipeline" : arr
				}


				#j = json.dumps(astage)
				#u = unicode(j, "utf-8")

				json_path = os.path.join(temp_dir, "TMR_%(name)s.json" % dict(name=self.name))

				with open(json_path, 'w') as json_file:
					json.dump(astage, json_file)

				#covert lidar to geotiff
				#pipeline = pdal.Pipeline(u)
				#count = pipeline.execute()

				subprocess.check_output('pdal pipeline {jfile}'.format(jfile=json_path), cwd=temp_dir, shell=True)

				output_file = os.path.join(target, self.output_file())
				mask.negative(os.path.join(temp_dir, "TMR_%(name)s.tif" % dict(name=self.name)), "GTiff", output_file)
				

	def freeze_dry(self):
		return dict(type='d96tm', link=self.link)

IS_D96TM_FILE = re.compile(
	'^b_([0-9]{2})/D96TM/TMR_([0-9]{2,3})_([0-9]{2,3}).laz')

def is_las(self):
	def func(tmp):
		if tmp.name.endswith(".laz"):
			return True
		else:
			return False	
	return func
	

def _parse_d96tm_tile(link, parent):
	m = IS_D96TM_FILE.match(link)

	if not m:
		return None

	d96_bottom = int(m.group(3)) * 1000
	d96_left = int(m.group(2)) * 1000
	d96_top = (int(m.group(3)) + 1) * 1000
	d96_right = (int(m.group(2)) + 1) * 1000

	block = int(m.group(1))
	name = m.group(2) + "_" + m.group(3)

	#D96 (EPSG::3794) to WGS84 (EPSG::4326)
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

	return D96TMTile(parent, link, name, block, bbox)

class D96TM(object):
	def __init__(self, options={}):
		self.base_dir = options.get('base_dir', 'd96tm')
		self.uri = options['uri']
		self.fishnet_url = options['fishnet_url']
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
		logger = logging.getLogger('d96tm')
		logger.info('Fetcthing D96TM index...')
		links = []

		fishnet = 'LIDAR_FISHNET_D96.shp'

		req = requests.get(self.fishnet_url, stream=True)
		with tmpdir.tmpdir() as d:
			with zipfile.ZipFile(io.BytesIO(req.content)) as zip_file:
					zip_file.extractall(d)

			fishnet_file = os.path.join(d, fishnet)
			driver = ogr.GetDriverByName("ESRI Shapefile")
			dataSource = driver.Open(fishnet_file, 1)
			layer = dataSource.GetLayer()

			for feature in layer:
				links.append(feature.GetField("BLOK") + "/D96TM/TMR_" + feature.GetField("NAME") + ".laz")
			layer.ResetReading()

		with open(index_file, 'w') as file:
			file.write(yaml.dump(links))

	def _ensure_tile_index(self):
		if self.tile_index is None:
			index_file = os.path.join(self.base_dir, 'index.yaml')
			bbox = (15.67583333,46.38861111,15.74166667,46.43305556)
			self.tile_index = index.create(index_file, bbox, _parse_d96tm_tile, self)

		return self.tile_index

	def existing_files(self):
		for base, dirs, files in os.walk(self.base_dir):
			for f in  files:
				if f.endswith('tif'):
					yield os.path.join(base, f)

	def rehydrate(self, data):
		assert data.get('type') == 'd96tm', \
			"Unable to rehydrate %r from Slovenia." %data
		return _parse_d96tm_tile(data['link'], self)

	def downloads_for(self, tile):
		tiles = set()
		# if the tile scale is greater than 20x the D96TM scale, then there's no
		# point in including D96TM, it'll be far too fine to make a difference.
		# D96TM is 1m.

		if tile.max_resolution() > 20:
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
		
		D96TM is non-overlapping.
		"""
		return [self.downloads_for(tile)]

	def srs(self):
		return srs.d96()

def create(options):
	return D96TM(options)