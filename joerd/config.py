from yaml import load
from util import BoundingBox
from joerd.region import Region
import copy


class Configuration(object):

    def __init__(self, yml):
        self.yml = yml
        self.regions = []
        for name, settings in self._cfg('regions').iteritems():
            self.regions.append(self._parse_region(settings))

        self.sources = self._cfg('sources')
        self.outputs = self._cfg('outputs')
        self.logconfig = self._cfg('logging config')
        self.queue_config = self._cfg('cluster queue')
        self.block_size = self._cfg('cluster block_size')
        self.store = self._cfg('store')
        self.source_store = self._cfg('source_store')

    def copy_with_regions(self, regions):
        """
        Copy this config, replacing the regions with those in the `regions`
        parameter.
        """

        new = copy.deepcopy(self)
        new.regions = []
        for region in regions:
            new.regions.append(self._parse_region(region))

        return new


    def _cfg(self, yamlkeys_str):
        yamlkeys = yamlkeys_str.split()
        yamlval = self.yml
        for subkey in yamlkeys:
            yamlval = yamlval[subkey]
        return yamlval


    def _parse_region(self, settings):
        box = settings['bbox']
        zoom_range = tuple(settings['zoom_range'])
        return Region(
            BoundingBox(box['left'], box['bottom'], box['right'],
                        box['top']), zoom_range)


def default_yml_config():
    return {
        'regions': {},
        'sources': [],
        'outputs': [],
        'logging': {
            'config': None
        },
        'cluster': {
            'queue': {
                'type': 'fake',
            },
            'block_size': 2,
        },
        'store': {
            'type': 'file',
            'base_dir': '.',
        },
        'source_store': {
            'type': 'file',
            'base_dir': '.',
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


def make_config_from_argparse(config, opencfg=open):
    # opencfg for testing
    cfg = default_yml_config()
    with opencfg(config.config) as config_fp:
        yml_data = load(config_fp.read())
        cfg = merge_cfg(cfg, yml_data)
    return Configuration(cfg)
