import boto3
from boto3.s3.transfer import TransferConfig
from os import walk
import os.path
from contextlib2 import contextmanager
from joerd.tmpdir import tmpdir
import traceback
import sys
import time


# extension to mime type mappings to help with serving the S3 bucket as
# a web site. if we add the content-type header on upload, then S3 will
# repeat it back when the tiles are accessed.
_MIME_TYPES = {
    '.png': 'image/png',
    '.tif': 'image/tif',
    '.xml': 'application/xml',
    '.gz': 'application/x-gzip',
}


# Stores files in S3
class S3Store(object):
    def __init__(self, cfg):
        self.bucket_name = cfg.get('bucket_name')
        self.upload_config = cfg.get('upload_config')

        assert self.bucket_name is not None, \
            "Bucket name not configured for S3 store, but it must be."

        # cache the boto resource and s3 bucket - we don't know what this
        # contains, so it seems safe to assume we can't pass it across a
        # multiprocessing boundary.
        self.s3 = None
        self.bucket = None

    # This object is likely to get pickled to send it to other processes
    # for multiprocessing. However, the s3/boto objects are probably not
    # safe to be pickled, so we'll just set them to None and regenerate
    # them on the other side.
    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['s3']
        del odict['bucket']
        return odict

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.s3 = None
        self.bucket = None

    def _get_bucket(self):
        if self.s3 is None or self.bucket is None:
            self.s3 = boto3.resource('s3')
            self.bucket = self.s3.Bucket(self.bucket_name)

        return self.bucket

    def upload_all(self, d):
        bucket = self._get_bucket()

        # strip trailing slashes so that we're sure that the path we create by
        # removing this as a prefix does not start with a /.
        if not d.endswith('/'):
            d = d + "/"

        transfer_config = TransferConfig(**self.upload_config)

        for dirpath, dirs, files in walk(d):
            if dirpath.startswith(d):
                suffix = dirpath[len(d):]
                self._upload_files(dirpath, suffix, files, transfer_config)

    def _upload_files(self, dirpath, suffix, files, transfer_config):
        for f in files:
            src_name = os.path.join(dirpath, f)
            s3_key = os.path.join(suffix, f)

            ext = os.path.splitext(f)[1]
            mime = _MIME_TYPES.get(ext)

            extra_args = {}
            if mime:
                extra_args['ContentType'] = mime

            # retry up to 6 times, waiting 32 (=2^5) seconds before the final
            # attempt.
            self.retry_upload_file(bucket, src_name, s3_key, transfer_config,
                                   extra_args, tries)

    def retry_upload_file(self, bucket, src_name, s3_key, transfer_config,
                          extra_args, tries, backoff=1):
        try_num = 0
        while True:
            try:
                bucket.upload_file(src_name, s3_key,
                                   Config=transfer_config,
                                   ExtraArgs=extra_args)
                break

            except StandardError:
                try_num += 1
                if try_num > tries:
                    raise

            time.sleep(backoff)
            backoff *= 2

    @contextmanager
    def upload_dir(self):
        with tmpdir() as t:
            yield t
            self.upload_all(t)

    def exists(self, filename):
        bucket = self._get_bucket()
        exists = False
        try:
            obj = bucket.Object(filename)
            obj.load()
        except ClientError as e:
            code = e.response['Error']['Code']
            # 403 is returned instead of 404 when the bucket doesn't allow
            # LIST operations, so treat that as missing as well.
            if code == "404" or code == "403":
                exists = False
            else:
                raise e
        else:
            exists = True

        return exists

    def get(self, source, dest):
        try:
            bucket = self._get_bucket()
            obj = bucket.Object(source)
            obj.download_file(dest)
        except:
            raise Exception("Failed to download %r, due to: %s"
                            % (source, "".join(traceback.format_exception(
                                *sys.exc_info()))))


def create(cfg):
    return S3Store(cfg)
