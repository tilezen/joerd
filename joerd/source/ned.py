from ned_base import NEDBase
import re
import os.path

NORMAL_PATTERN = re.compile('^ned19_' \
                            '([ns])([0-9]{2})x([0257][05])_' \
                            '([ew])([0-9]{3})x([0257][05])_' \
                            '[a-z]{2}_[a-z]+_20[0-9]{2}.(zip|img)$')


class NED(NEDBase):
    def __init__(self, regions, options={}):
        self.pattern = NORMAL_PATTERN
        super(NED, self).__init__(regions, options)

    def vrt_file(self):
        return os.path.join(self.base_dir, "ned.vrt")

    def mask_negative(self):
        return True


def create(regions, options):
    return NED(regions, options)
