#!/usr/bin/env python
from __future__ import print_function
from math import log, tan, pi
from itertools import product
from argparse import ArgumentParser
from os.path import join, splitext

import tempfile, shutil, urllib, io, sys, subprocess
import unittest

# four formats are available, let's use GeoTIFF
tile_url = 'https://tile.mapzen.com/mapzen/terrain/v1/geotiff/{z}/{x}/{y}.tif?api_key={k}'

# default API key, please set your own
default_api_key = 'mapzen-SPsSJJY'

def mercator(lat, lon, zoom):
    ''' Convert latitude, longitude to z/x/y tile coordinate at given zoom.
    '''
    # convert to radians
    x1, y1 = lon * pi/180, lat * pi/180

    # project to mercator
    x2, y2 = x1, log(tan(0.25 * pi + 0.5 * y1))

    # transform to tile space
    tiles, diameter = 2 ** zoom, 2 * pi
    x3, y3 = int(tiles * (x2 + pi) / diameter), int(tiles * (pi - y2) / diameter)

    return zoom, x3, y3

def tiles(zoom, lat1, lon1, lat2, lon2):
    ''' Convert geographic bounds into a list of tile coordinates at given zoom.
    '''
    # convert to geographic bounding box
    minlat, minlon = min(lat1, lat2), min(lon1, lon2)
    maxlat, maxlon = max(lat1, lat2), max(lon1, lon2)

    # convert to tile-space bounding box
    _, xmin, ymin = mercator(maxlat, minlon, zoom)
    _, xmax, ymax = mercator(minlat, maxlon, zoom)

    # generate a list of tiles
    xs, ys = range(xmin, xmax+1), range(ymin, ymax+1)
    tiles = [(zoom, x, y) for (y, x) in product(ys, xs)]

    return tiles

def download(output_path, tiles, api_key, verbose=True):
    ''' Download list of tiles to a temporary directory and return its name.
    '''
    dir = tempfile.mkdtemp(prefix='collected-')
    _, ext = splitext(output_path)

    merge_geotiff = bool(ext.lower() in ('.tif', '.tiff', '.geotiff'))

    try:
        files = []

        for (z, x, y) in tiles:
            response = urllib.urlopen(tile_url.format(z=z, x=x, y=y, k=api_key))
            if response.getcode() != 200:
                raise RuntimeError('No such tile: {}'.format((z, x, y)))
            if verbose:
                print('Downloaded', response.url, file=sys.stderr)

            with io.open(join(dir, '{}-{}-{}.tif'.format(z, x, y)), 'wb') as file:
                file.write(response.read())
                files.append(file.name)

        if merge_geotiff:
            if verbose:
                print('Combining', len(files), 'into', output_path, '...', file=sys.stderr)
            temp_tif = join(dir, 'temp.tif')
            subprocess.check_call(['gdal_merge.py', '-o', temp_tif] + files)
            shutil.move(temp_tif, output_path)
        else:
            if verbose:
                print('Moving', dir, 'to', output_path, '...', file=sys.stderr)
            shutil.move(dir, output_path)

    finally:
        if merge_geotiff:
            shutil.rmtree(dir)

class TestCollect (unittest.TestCase):

    def test_mercator(self):
        self.assertEqual(mercator(0, 0, 0), (0, 0, 0))
        self.assertEqual(mercator(0, 0, 16), (16, 32768, 32768))
        self.assertEqual(mercator(37.79125, -122.39197, 16), (16, 10487, 25327))
        self.assertEqual(mercator(40.74418, -73.99047, 16), (16, 19298, 24632))
        self.assertEqual(mercator(-35.30816, 149.12446, 16), (16, 59915, 39645))

    def test_tiles(self):
        self.assertEqual(tiles(16, 37.79125, -122.39197, 37.79125, -122.39197), [(16, 10487, 25327)])
        self.assertEqual(tiles(16, 0.00034, -0.00056, -0.00034, 0.00043), [(16, 32767, 32767), (16, 32768, 32767), (16, 32767, 32768), (16, 32768, 32768)])
        self.assertEqual(tiles(16, -0.00034, 0.00043, 0.00034, -0.00056), [(16, 32767, 32767), (16, 32768, 32767), (16, 32767, 32768), (16, 32768, 32768)])

    def test_download_tilebag(self):
        with mock.patch('io.open') as open, \
             mock.patch('shutil.move') as move, \
             mock.patch('shutil.rmtree') as rmtree, \
             mock.patch('tempfile.mkdtemp') as mkdtemp, \
             mock.patch('urllib.urlopen') as urlopen, \
             mock.patch('subprocess.check_call') as check_call:

            mkdtemp.return_value = '/tmp'
            urlopen.return_value.getcode.return_value = 200
            open.return_value.__enter__.return_value.name = '/tmp/tile.tif'

            download('/tmp/output', [
                (12, 656, 1582),
                (12, 657, 1582),
                (12, 658, 1582),
                ], False)

            self.assertEqual(len(rmtree.mock_calls), 0)
            self.assertEqual(len(check_call.mock_calls), 0)

            self.assertEqual(urlopen.mock_calls[::3], [
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/656/1582.tif?api_key=mapzen-SPsSJJY'),
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/657/1582.tif?api_key=mapzen-SPsSJJY'),
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/658/1582.tif?api_key=mapzen-SPsSJJY')
                ])

            move.assert_called_once_with('/tmp', '/tmp/output')

    def test_download_merge(self):
        with mock.patch('io.open') as open, \
             mock.patch('shutil.move') as move, \
             mock.patch('shutil.rmtree') as rmtree, \
             mock.patch('tempfile.mkdtemp') as mkdtemp, \
             mock.patch('urllib.urlopen') as urlopen, \
             mock.patch('subprocess.check_call') as check_call:

            mkdtemp.return_value = '/tmp'
            urlopen.return_value.getcode.return_value = 200
            open.return_value.__enter__.return_value.name = '/tmp/tile.tif'

            download('/tmp/output.tif', [
                (12, 656, 1582),
                (12, 657, 1582),
                (12, 658, 1582),
                ], False)

            rmtree.assert_called_once_with(tempfile.mkdtemp.return_value)

            self.assertEqual(urlopen.mock_calls[::3], [
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/656/1582.tif?api_key=mapzen-SPsSJJY'),
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/657/1582.tif?api_key=mapzen-SPsSJJY'),
                mock.call('https://tile.mapzen.com/mapzen/terrain/v1/geotiff/12/658/1582.tif?api_key=mapzen-SPsSJJY')
                ])

            check_call.assert_called_once_with(['gdal_merge.py', '-o', '/tmp/temp.tif', '/tmp/tile.tif', '/tmp/tile.tif', '/tmp/tile.tif'])
            move.assert_called_once_with('/tmp/temp.tif', '/tmp/output.tif')

parser = ArgumentParser(description='''Collect Mapzen elevation tiles into a
single GeoTIFF or directory. If output_path ends in ".tif", ".tiff", or
".geotiff", gdal_merge.py will be called to merge all downloaded tiles into a
single image. Otherwise, they are collected into the named directory.''')

parser.add_argument('--testing', action='store_const', const=True, default=False,
                    help='If set, run unit tests and bail out.')

parser.add_argument('--bounds', metavar='DEG', type=float, nargs=4,
                    default=(37.8434, -122.3193, 37.7517, -122.0927),
                    help='Geographic bounds given as two lat/lon pairs. Defaults to Oakland, CA hills.')

parser.add_argument('--zoom', type=int, default=12,
                    help='Map zoom level given as integer. Defaults to 12.')

parser.add_argument('--mapzen_api_key', default=default_api_key,
                    help='Mapzen API key required to use the terrain tile service. See: https://mapzen.com/documentation/overview/#developer-accounts-and-api-keys.')

parser.add_argument('output_path', help='Output GeoTIFF filename or local directory name.')

if __name__ == '__main__':
    args = parser.parse_args()

    if args.testing:
        import mock # To run tests, `pip install mock==2.0.0`
        suite = unittest.defaultTestLoader.loadTestsFromName(__name__)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        exit(0 if result.wasSuccessful() else 1)

    download(args.output_path, tiles(args.zoom, *args.bounds), args.mapzen_api_key)
