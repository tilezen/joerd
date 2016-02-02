from config import make_config_from_argparse
from osgeo import gdal
from importlib import import_module
from multiprocessing import Pool
import sys
import argparse
import os
import logging
import logging.config


def create_command_parser(fn):
    def create_parser_fn(parser):
        parser.add_argument('--config', required=True,
                            help='The path to the joerd config file.')
        parser.set_defaults(func=fn)
        return parser
    return create_parser_fn


def _mktile(t):
    output, tile = t
    output.process_tile(tile)


class Joerd:

    def __init__(self, cfg):
        self.sources = self._sources(cfg)
        self.outputs = self._outputs(cfg, self.sources)

    def download(self):
        for source in self.sources:
            source.download()

    def buildvrt(self):
        for source in self.sources:
            source.buildvrt()

    def generate(self):
        tiles = []

        for output in self.outputs:
            tiles.extend([(output, t) for t in output.generate_tiles()])

        p = Pool()
        try:
            p.map(_mktile, tiles)

        finally:
            p.close()
            p.join()

    def _sources(self, cfg):
        sources = []
        for source in cfg.sources:
            source_type = source['type']
            module = import_module('joerd.source.%s' % source_type)
            create_fn = getattr(module, 'create')
            sources.append(create_fn(cfg.regions, source))
        return sources

    def _outputs(self, cfg, sources):
        outputs = []
        for output in cfg.outputs:
            output_type = output['type']
            module = import_module('joerd.output.%s' % output_type)
            create_fn = getattr(module, 'create')
            outputs.append(create_fn(cfg.regions, sources, output))
        return outputs


class JoerdArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def joerd_download(cfg):
    j = Joerd(cfg)
    j.download()


def joerd_buildvrt(cfg):
    j = Joerd(cfg)
    j.buildvrt()


def joerd_generate(cfg):
    j = Joerd(cfg)
    j.generate()


def joerd_main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # check the actually installed GDAL version
    gdal_version = gdal.VersionInfo()
    gdal_major_version = int(gdal_version)/1000000
    assert gdal_major_version >= 2, \
        'Joerd needs GDAL >= 2.0.0, but got %r' % gdal_version

    parser = JoerdArgumentParser()
    subparsers = parser.add_subparsers()

    parser_config = (
        ('download', create_command_parser(joerd_download)),
        ('buildvrt', create_command_parser(joerd_buildvrt)),
        ('generate', create_command_parser(joerd_generate)),
    )

    for name, func in parser_config:
        subparser = subparsers.add_parser(name)
        func(subparser)

    args = parser.parse_args(argv)
    assert os.path.exists(args.config), \
        'Config file %r does not exist.' % args.config
    cfg = make_config_from_argparse(args.config)

    if cfg.logconfig is not None:
        logging.config.fileConfig(cfg.logconfig)

    args.func(cfg)
