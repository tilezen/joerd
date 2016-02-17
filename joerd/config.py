from yaml import load
from util import BoundingBox
from multiprocessing import cpu_count
from joerd.region import Region


class Configuration(object):

    def __init__(self, yml):
        self.yml = yml
        self.regions = []
        for name, settings in self._cfg('regions').iteritems():
            box = settings['bbox']
            zoom_range = tuple(settings['zoom_range'])
            self.regions.append(Region(
                BoundingBox(box['left'], box['bottom'], box['right'],
                            box['top']), zoom_range))

        self.sources = self._cfg('sources')
        self.outputs = self._cfg('outputs')
        self.logconfig = self._cfg('logging config')
        self.num_threads = self._cfg('jobs num_threads')
        self.chunksize = self._cfg('jobs chunksize')


    def _cfg(self, yamlkeys_str):
        yamlkeys = yamlkeys_str.split()
        yamlval = self.yml
        for subkey in yamlkeys:
            yamlval = yamlval[subkey]
        return yamlval


def default_yml_config():
    return {
        'regions': {},
        'sources': [],
        'outputs': [],
        'logging': {
            'config': None
        },
        'jobs': {
            'num_threads': cpu_count(),
            'chunksize': None,
        },
    }


def merge_cfg(dest, source):
    for k, v in source.items():
        if isinstance(v, dict):
            subdest = dest.setdefault(k, {})
            merge_cfg(subdest, v)
        else:
            dest[k] = v
    return dest


def make_config_from_argparse(config_path, opencfg=open):
    # opencfg for testing
    cfg = default_yml_config()
    with opencfg(config_path) as config_fp:
        yml_data = load(config_fp.read())
        cfg = merge_cfg(cfg, yml_data)
    return Configuration(cfg)
