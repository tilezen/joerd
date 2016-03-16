from distutils.dir_util import copy_tree
from contextlib2 import contextmanager
from joerd.tmpdir import tmpdir

# Stores files in a directory (defaults to the current directory)
class FileStore(object):
    def __init__(self, cfg):
        self.base_dir = cfg.get('base_dir', '.')

    def upload_all(self, d):
        copy_tree(d, self.base_dir)

    @contextmanager
    def upload_dir(self):
        with tmpdir() as t:
            yield t
            self.upload_all(t)

    def exists(self, filename):
        return os.path.exists(os.path.join(self.base_dir, filename))

def create(cfg):
    return FileStore(cfg)
