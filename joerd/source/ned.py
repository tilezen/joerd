from ned_base import NEDBase
import re
import os.path

NORMAL_PATTERN = re.compile('^ned19_' \
                            '([ns])([0-9]{2})x([0257][05])_' \
                            '([ew])([0-9]{3})x([0257][05])_' \
                            '[a-z]{2}_[a-z]+_20[0-9]{2}.(zip|img)$')


class NED(object):
    def __init__(self, regions, options={}):
        options = options.copy()
        options.update(dict(
            pattern=NORMAL_PATTERN,
            vrt_file="ned.vrt"))
        self.base = NEDBase(regions, options)

    def download(self):
        self.base.download()

    def buildvrt(self):
        self.base.buildvrt()

    def filter_type(self, src_res, dst_res):
        return self.base.filter_type(src_res, dst_res)

    def vrt_file(self):
        return self.base.vrt_file()

    def mask_negative(self):
        return True


def create(regions, options):
    return NED(regions, options)
