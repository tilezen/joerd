from distutils.dir_util import copy_tree

# Stores files in a directory (defaults to the current directory)
class FileStore(object):
    def __init__(self, cfg):
        self.base_dir = cfg.get('base_dir', '.')

    def upload_all(self, d):
        copy_tree(d, self.base_dir)


def create(cfg):
    return FileStore(cfg)
