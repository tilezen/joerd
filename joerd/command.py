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
    size_limit = 256 * 1024
    dispatcher = GroupingDispatcher(queue, max_batch_len, logger, size_limit)

    for output in j.outputs.itervalues():
        for tile in output.generate_tiles():
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
