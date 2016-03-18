from config import make_config_from_argparse
from osgeo import gdal
from joerd.server import Server
from joerd.plugin import plugin
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


def joerd_server(global_cfg):
    logger = logging.getLogger('process')

    j = Server(global_cfg)
    queue = _make_queue(j, global_cfg.queue_config)

    while True:
        for message in queue.receive_messages():
            job = message.body

            try:
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
    Sends each region in the config file to the queue for processing by workers.
    """

    logger = logging.getLogger('enqueuer')

    j = Server(cfg)

    logger.info("Streaming jobs to the queue")
    queue = _make_queue(j, cfg.queue_config)

    batch = []
    idx = 0
    next_log_idx = 0

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
                "but it has none." % tile

            job = dict(job='render', data=tile.freeze_dry(), sources=sources)
            batch.append(job)
            idx += 1

            if len(batch) == queue.batch_size():
                try:
                    queue.send_messages(batch)
                except StandardError as e:
                    logger.warning("Failed to enqueue batch: %s" \
                                   % "".join(traceback.format_exception(
                                       *sys.exc_info())))
                    batch = []

            if idx >= next_log_idx:
                logger.info("Sent %d jobs to queue." % idx)
                next_log_idx += 1000

    if len(batch) > 0:
        try:
            queue.send_messages(batch)
        except StandardError as e:
            logger.warning("Failed to enqueue batch: %s" \
                           % "".join(traceback.format_exception(
                               *sys.exc_info())))

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

    batch = []

    for d in downloads:
        data = d.freeze_dry()
        job = dict(job='download', data=data)
        batch.append(job)

        if len(batch) == queue.batch_size():
            try:
                queue.send_messages(batch)
            except StandardError as e:
                logger.warning("Failed to enqueue batch: %s" \
                               % "".join(traceback.format_exception(
                                   *sys.exc_info())))
            batch = []

    if len(batch) > 0:
        try:
            queue.send_messages(batch)
        except StandardError as e:
            logger.warning("Failed to enqueue batch: %s" \
                           % "".join(traceback.format_exception(
                               *sys.exc_info())))

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
