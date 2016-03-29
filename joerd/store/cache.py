from joerd.mkdir_p import mkdir_p
from joerd.plugin import plugin
from os import link
from contextlib2 import contextmanager
import os.path


class CacheStore(object):
    """
    Every tile that gets generated requires ETOPO1. Rather than re-download
    it every time (it's 446MB), we cache that file only.

    This is a bit of a hack, and would be better replaced by a generic
    fixed-size LRU/LFU cache. Even better if the cache could be shared
    between multiple Joerd processes on the same host.
    """

    def __init__(self, cfg):
        store_type = cfg['store']['type']
        create_fn = plugin('store', store_type, 'create')
        self.store = create_fn('store', cfg['store'])
        self.cache_dir = cfg['cache_dir']

    def upload_all(self, d):
        self.store.upload_all(d)

    @contextmanager
    def upload_dir(self):
        with tmpdir() as t:
            yield t
            self.upload_all(t)

    def exists(self, filename):
        return self.store.exists(filename)

    def get(self, source, dest):
        if 'ETOPO1' in source:
            cache_path = os.path.join(self.cache_dir, source)
            if not os.path.exists(cache_path):
                mkdir_p(os.path.dirname(cache_path))
                self.store.get(source, cache_path)

            # hard link to dest. this makes it non-portable, but means that
            # we don't have to worry about whether GDAL supports symbolic
            # links, and we don't have to worry about deleting files, as they
            # are reference counted by the OS.
            link(cache_path, dest)

        else:
            self.store.get(source, dest)


def create(cfg):
    return CacheStore(cfg)
