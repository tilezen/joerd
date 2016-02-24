from ned_base import NEDBase
import re
import os.path


TOPOBATHY_PATTERN = re.compile('^ned19_' \
                               '([ns])([0-9]{2})x([0257][05])_' \
                               '([ew])([0-9]{3})x([0257][05])_' \
                               '[a-z]{2}_[a-z]+_topobathy_20[0-9]{2}.' \
                               '(zip|img)$')


class NEDTopobathy(object):
    def __init__(self, options={}):
        options = options.copy()
        options['pattern'] = TOPOBATHY_PATTERN
        options['base_dir'] = options.get('base_dir', 'ned_topobathy')
        self.base = NEDBase(True, options)

    def get_index(self):
        return self.base.get_index()

    def downloads_for(self, tile):
        return self.base.downloads_for(tile)

    def vrts_for(self, tile):
        return self.base.vrts_for(tile)

    def filter_type(self, src_res, dst_res):
        return self.base.filter_type(src_res, dst_res)

    def srs(self):
        return self.base.srs()


def create(options):
    return NEDTopobathy(options)
