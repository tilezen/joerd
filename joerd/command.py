from config import make_config_from_argparse
from osgeo import gdal
from joerd.server import Server
from joerd.plugin import plugin
from joerd.dispatcher import Dispatcher, GroupingDispatcher
import sys
import argparse
import os
import os.path
import logging
import logging.config
import time
import traceback
import json
import math


def _make_queue(j, config):
    """
    Makes a queue object by looking up the plugin module mentioned in the type
    parameter of the configuration.
    """
    typ = config['type']
    create_fn = plugin('queue', typ, 'create')
    return create_fn(j, config)


def create_command_parser(fn):
    def create_parser_fn(parser):
        parser.add_argument('--config', required=True,
                            help='The path to the joerd config file.')
        parser.add_argument('--jobs-file', required=False,
                            help='The path to the list of jobs to run for the '
                            'enqueuer.')
        parser.set_defaults(func=fn)
        return parser
    return create_parser_fn


class JoerdArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def joerd_server(cfg):
    """
    Runs a server in an infinite loop.

    This grabs jobs from the queue and processes them. Jobs which cannot be
    processed due to an error are ignored and the next job is processed.
    """
    logger = logging.getLogger('process')

    j = Server(cfg)
    queue = _make_queue(j, cfg.queue_config)

    while True:
        for message in queue.receive_messages():
            jobs = message.body

            try:
                for job in jobs:
                    j.dispatch_job(job)

            except StandardError as e:
                logger.warning("During processing of job %r, caught "
                               "exception. This job failed, continuing "
                               "to the next. Exception details: %s" %
                               (job, "".join(traceback.format_exception(
                                   *sys.exc_info()))))
            else:
                # remove the message from the queue - this indicates that
                # it has completed successfully and it won't be retried.
                message.delete()


def joerd_enqueue_renders(cfg):
    """
    Sends each output tile configured for the regions in the config file to
    the queue for processing by workers.

    Note that downloading to the store should have happened before this is
    run, as the render process has no way to download files.
    """

    logger = logging.getLogger('enqueuer')

    j = Server(cfg)

    logger.info("Streaming jobs to the queue")
    queue = _make_queue(j, cfg.queue_config)

    max_batch_len = 1000
    # size limit is 256KB for SQS, but we'll leave a little bit of space
    # just in case there's some small overhead for encoding it as an array.
    size_limit = 256 * 1024 - 100
    dispatcher = GroupingDispatcher(queue, max_batch_len, logger, size_limit)

    idx = 0
    next_idx = 0

    logger.info("Starting loop")
    for output in j.outputs.itervalues():
        logger.info("Starting output %r" % output.__class__.__name__)
        for tile in output.generate_tiles():
            if idx >= next_idx:
                next_idx += 10000
                logger.info("[%d] At job %r" % (idx, tile.__class__.__name__))
            idx += 1
            sources = []
            for name, s in j.sources:
                v = s.vrts_for(tile)
                if v:
                    vrts = []
                    for rasters in v:
                        files = [r.output_file() for r in rasters]
                        if files:
                            vrts.append(files)
                    if vrts:
                        sources.append(dict(source=name, vrts=vrts))

            assert sources, "Was expecting at least one source for tile %r, " \
                "but it has none." % tile.tile_name()

            job = dict(job='render', data=tile.freeze_dry(), sources=sources)
            dispatcher.append(job)

    dispatcher.flush()
    logger.info("Done.")


def joerd_enqueue_single_renders(cfg):
    """
    Renders single tiles without a queue. The list of tiles is read from a file
    called `tiles_to_enqueue.txt`. Can be useful for testing.
    """

    logger = logging.getLogger('enqueuer')

    j = Server(cfg)

    logger.info("Fetching download information")
    j.list_downloads()

    logger.info("Streaming jobs to the queue")
    queue = _make_queue(j, cfg.queue_config)

    max_batch_len = 1000
    # size limit is 256KB for SQS, but we'll leave a little bit of space
    # just in case there's some small overhead for encoding it as an array.
    size_limit = 256 * 1024 - 100
    dispatcher = GroupingDispatcher(queue, max_batch_len, logger, size_limit)

    idx = 0
    next_idx = 0

    tiff_output = j.outputs['tiff']
    normal_output = j.outputs['normal']
    terrarium_output = j.outputs['terrarium']

    import joerd.output as output

    logger.info("Starting loop")
    with open('tiles_to_enqueue.txt', 'r') as fh:
        for line in fh:
            location = line.split(".")[0]
            tile = None

            if location.startswith('skadi/'):
                output_name, y, tile_name = location.split("/")
                pos = output.skadi._parse_tile(tile_name)
                if pos is None:
                    raise Exception, "Couldn't parse skadi tile name %r" \
                        % tile_name
                tile = output.skadi.SkadiTile('skadi', *pos)

            else:
                output_name, z, x, y = location.split("/")
                z = int(z)
                x = int(x)
                y = int(y)

                if output_name == 'geotiff':
                    tile = output.tiff.TiffTile(tiff_output, z, x, y)
                elif output_name == 'normal':
                    tile = output.normal.NormalTile(normal_output, z, x, y)
                elif output_name == 'terrarium':
                    tile = output.terrarium.TerrariumTile(terrarium_output,
                                                          z, x, y)
                else:
                    raise Exception, "Couldn't make a tile from line %r" \
                        % line

            sources = []
            for name, s in j.sources:
                v = s.vrts_for(tile)
                if v:
                    vrts = []
                    for rasters in v:
                        files = [r.output_file() for r in rasters]
                        if files:
                            vrts.append(files)
                    if vrts:
                        sources.append(dict(source=name, vrts=vrts))

            assert sources, "Was expecting at least one source for tile %r, " \
                "but it has none." % tile.tile_name()

            job = dict(job='render', data=tile.freeze_dry(), sources=sources)
            dispatcher.append(job)

    dispatcher.flush()
    logger.info("Done.")


def joerd_enqueue_downloads(cfg):
    """
    Sends a list of all the source files needed for rendering the configured
    regions in the config file to the queue for downloading by workers.
    """

    logger = logging.getLogger('enqueuer')

    j = Server(cfg)
    downloads = j.list_downloads()

    logger.info("Sending %d download jobs to the queue" % len(downloads))
    queue = _make_queue(j, cfg.queue_config)

    # download jobs are long-running and don't benefit from any cache re-use,
    # so don't batch them - just one job per batch.
    max_batch_len = 1
    dispatcher = Dispatcher(queue, max_batch_len, logger)

    # env var to turn on/off skipping existing files. this can be useful when
    # re-running the jobs for a particular area.
    skip_existing = os.getenv('SKIP_EXISTING', False)

    for d in downloads:
        # skip any files which already exist.
        if skip_existing and j.source_store.exists(d.output_file()):
            continue

        data = d.freeze_dry()
        job = dict(job='download', data=data)
        dispatcher.append(job)

    dispatcher.flush()
    logger.info("Done.")


def joerd_main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = JoerdArgumentParser()
    subparsers = parser.add_subparsers()

    parser_config = (
        ('server', create_command_parser(joerd_server)),
        ('enqueue-renders', create_command_parser(joerd_enqueue_renders)),
        ('enqueue-single-renders', create_command_parser(joerd_enqueue_single_renders)),
        ('enqueue-downloads', create_command_parser(joerd_enqueue_downloads)),
    )

    for name, func in parser_config:
        subparser = subparsers.add_parser(name)
        func(subparser)

    args = parser.parse_args(argv)
    assert os.path.exists(args.config), \
        'Config file %r does not exist.' % args.config
    cfg = make_config_from_argparse(args)

    if cfg.logconfig is not None:
        config_dir = os.path.dirname(args.config)
        logconfig_path = os.path.join(config_dir, cfg.logconfig)
        logging.config.fileConfig(logconfig_path)

    # make sure process will error if GDAL fails
    gdal.UseExceptions()

    args.func(cfg)
