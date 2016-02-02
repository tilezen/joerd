from joerd.util import BoundingBox
from multiprocessing import Pool
from contextlib import closing
from shutil import copyfile
from ftplib import FTP
import os.path
import os
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
import urllib2
import shutil


def __download_ned_file(img_name, zip_name, base_dir, ftp_server, base_path):
    logger = logging.getLogger('ned')
    output_file = os.path.join(base_dir, img_name)

    if os.path.isfile(output_file):
        return output_file

    with closing(tempfile.NamedTemporaryFile()) as tmp:
        url = 'ftp://%s/%s/%s' % (ftp_server, base_path, zip_name)
        logger.info("FTP: Fetching %r" % url)

        with closing(urllib2.urlopen(url)) as req:
            shutil.copyfileobj(req, tmp)

        tmp.flush()

        with zipfile.ZipFile(tmp.name, 'r') as zfile:
            zfile.extract(img_name, base_dir)
            zfile.extract(img_name + ".aux.xml", base_dir)

    return output_file


def _download_ned_file(img_name, zip_name, base_dir, ftp_server, base_path):
    try:
        return __download_ned_file(img_name, zip_name, base_dir, ftp_server,
                                   base_path)
    except:
        print>>sys.stderr, "Caught exception: %s" % \
            ("\n".join(traceback.format_exception(*sys.exc_info())))
        raise


def _parallel(func, iterable, num_threads=None):
    p = Pool(processes=num_threads)
    threads = []

    for x in iterable:
        p.apply_async(func, x)

    p.close()
    return_values = []
    for t in threads:
        return_values.append(t.get())

    p.join()
    return return_values


class NEDBase(object):

    def __init__(self, regions, options={}):
        self.regions = regions
        self.num_download_threads = options.get('num_download_threads')
        self.base_dir = options.get('base_dir', 'ned')
        self.ftp_server = options['ftp_server']
        self.base_path = options['base_path']
        self.pattern = re.compile(options['pattern'])
        self.vrt_filename = options['vrt_file']

    def download(self):
        logger = logging.getLogger('ned')
        logger.info('Fetching NED index...')

        files = []
        for bbox, fname, zname in self._list_ned_files():
            if self._intersects(bbox):
                files.append((fname, zname))

        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

        logger.info("Starting download of %d NED files." % len(files))
        files = _parallel(
            _download_ned_file,
            [(f, z, self.base_dir, self.ftp_server, self.base_path)
             for f, z in files],
            num_threads=self.num_download_threads)

        # sanity check
        for f, z in files:
            assert os.path.isfile(os.path.join(self.base_dir, f))

        logger.info("Download complete.")

    def buildvrt(self):
        logger = logging.getLogger('ned')
        logger.info("Creating VRT.")

        files = []
        for f in glob.glob(os.path.join(self.base_dir, '*.img')):
            bbox = self._ned_parse_filename(os.path.split(f)[1])
            if bbox and self._intersects(bbox):
                files.append(f)

        args = ["gdalbuildvrt", "-q", self.vrt_file] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        assert os.path.isfile(self.vrt_file)

        logger.info("VRT created.")

    def filter_type(self):
        return gdal.GRA_Lanczos

    def vrt_file(self):
        return os.path.join(self.base_path, self.vrt_filename)

    def _intersects(self, bbox):
        for r in self.regions:
            if r.intersects(bbox):
                return True
        return False

    def _list_ned_files(self):
        ftp = FTP(self.ftp_server)
        files = []

        def _callback(zname):
            bbox = self._ned_parse_filename(zname)
            if bbox is not None:
                fname = zname.replace(".zip", ".img")
                files.append((bbox, fname, zname))

        ftp.login()
        ftp.cwd(self.base_path)
        try:
            ftp.set_pasv(True)
            ftp.retrlines('NLST', _callback)
            ftp.quit()
        except EOFError:
            pass

        return files


    def _ned_parse_filename(self, fname):
        m = self.pattern.match(fname)

        if m:
            y = int(m.group(2)) + float(m.group(3)) / 100.0
            x = int(m.group(5)) + float(m.group(6)) / 100.0
            if m.group(1) == 's':
                y = -y
            if m.group(4) == 'w':
                x = -x
            return BoundingBox(x, y - 0.25, x + 0.25, y)

        return None
