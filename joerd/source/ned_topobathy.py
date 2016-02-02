from ned_base import NEDBase
import re
import os.path


TOPOBATHY_PATTERN = re.compile('^ned19_' \
                               '([ns])([0-9]{2})x([0257][05])_' \
                               '([ew])([0-9]{3})x([0257][05])_' \
                               '[a-z]{2}_[a-z]+_topobathy_20[0-9]{2}.' \
                               '(zip|img)$')


class NEDTopobathy(object):
    def __init__(self, regions, options={}):
        options.update(dict(
            pattern=TOPOBATHY_PATTERN,
            vrt_file="ned_topobathy.vrt"))
        self.base = NEDBase(regions, options)

    def download(self):
        self.base.download()

    def buildvrt(self):
        self.base.buildvrt()

    def filter_type(self):
        return self.base.filter_type()

    def vrt_file(self):
        return self.base.vrt_file()

    def mask_negative(self):
        return False


def create(regions, options):
    return NEDTopobathy(regions, options)
