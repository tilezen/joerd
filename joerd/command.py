from config import make_config_from_argparse
from osgeo import gdal
from importlib import import_module
from multiprocessing import Pool
import joerd.download as download
import sys
import argparse
import os
import os.path
import logging
import logging.config
import time
import traceback
import json
import boto3


def create_command_parser(fn):
    def create_parser_fn(parser):
        parser.add_argument('--config', required=True,
                            help='The path to the joerd config file.')
        parser.set_defaults(func=fn)
        return parser
    return create_parser_fn


def _download(d):
    options = d.options().copy()
    options['verifier'] = d.verifier()

    with download.get(d.url(), options) as tmp:
        d.unpack(tmp)

    assert os.path.isfile(d.output_file())


def _render(t):
    try:
        t.render()
    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


# ProgressLogger - logs progress towards a goal to the given logger.
# This is useful for letting the user know that something is happening, and
# roughly how far along it is. Progress is logged at given percentage
# intervals or time intervals, whichever is crossed first.
class ProgressLogger(object):
    def __init__(self, logger, total, time_interval=10, pct_interval=5):
        self.logger = logger
        self.total = total
        self.progress = 0
        self.time_interval = time_interval
        self.pct_interval = pct_interval

        self.next_time = time.time() + self.time_interval
        self.next_pct = self.pct_interval

    def increment(self, amount):
        self.progress += amount
        pct = (100.0 * self.progress) / self.total
        now = time.time()

        if pct > self.next_pct or now > self.next_time:
            self.next_pct = pct + self.pct_interval
            self.next_time = now + self.time_interval
            self.logger.info("Progress: %3.1f%%" % pct)


class Joerd:

    def __init__(self, cfg):
        self.sources = self._sources(cfg)
        self.outputs = self._outputs(cfg, self.sources)
        self.num_threads = cfg.num_threads
        self.chunksize = cfg.chunksize

    def process(self):
        logger = logging.getLogger('process')

        # fetch index for each source, which speeds up subsequent downloads or
        # queries about which source tiles are available.
        for source in self.sources:
            source.get_index()

        # get the list of all tiles to be generated
        tiles = []
        for output in self.outputs:
            tiles.extend(output.generate_tiles())

        logger.info("Will generate %d tiles." % len(tiles))

        # gather the set of all downloads - upstream source tiles - for all the
        # tiles that will be generated.
        downloads = set()
        progress = ProgressLogger(logger, len(tiles))
        for tile in tiles:
            # each tile intersects a set of downloads for each source, perhaps
            # an empty set. to track those, only sources which intersect the
            # tile are tracked.
            tile_sources = []
            for source in self.sources:
                d = source.downloads_for(tile)
                if d:
                    downloads.update(d)
                    tile_sources.append(source)
            tile.set_sources(tile_sources)
            progress.increment(1)

        p = Pool(processes=self.num_threads)

        # grab a list of the files which aren't currently available
        need_to_download = []
        for download in downloads:
            if not os.path.isfile(download.output_file()):
                need_to_download.append(download)

        logger.info("Need to download %d source files."
                    % len(need_to_download))

        p.map(_download, need_to_download,
              chunksize=self._chunksize(len(need_to_download)))

        logger.info("Starting render of %d tiles." % len(tiles))

        # now render the tiles
        p.map(_render, tiles, chunksize=self._chunksize(len(tiles)))

        # clean up the Pool.
        p.close()
        p.join()

    def _chunksize(self, length):
        """
        Try to determine an appropriate chunk size. The bigger the chunk, the
        lower the overheads, but potentially worse load balance between the
        different threads. A compromise is a fixed fraction of the maximum
        chunk size - in this case, an eighth.

        Chunksize can be overridden in the config, in which case this
        heuristic is ignored.
        """
        if self.chunksize is not None:
              return self.chunksize
        return max(1, length / self.num_threads / 8)

    def _sources(self, cfg):
        sources = []
        for source in cfg.sources:
            source_type = source['type']
            module = import_module('joerd.source.%s' % source_type)
            create_fn = getattr(module, 'create')
            sources.append(create_fn(source))
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


def joerd_process(cfg):
    j = Joerd(cfg)
    j.process()


def joerd_server(global_cfg):
    assert cfg.sqs_queue_name is not None, \
        "Could not find SQS queue name in config, but this must be configured."

    sqs = boto3.resource('sqs')
    queue = sqs.Queue(cfg.sqs_queue_name)

    while True:
        for message in queue.get_messages():
            region = json.loads(message.body)
            cfg = global_cfg.copy_with_regions([region])
            joerd_process(cfg)


def joerd_main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = JoerdArgumentParser()
    subparsers = parser.add_subparsers()

    parser_config = (
        ('process', create_command_parser(joerd_process)),
        ('server', create_command_parser(joerd_server)),
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
