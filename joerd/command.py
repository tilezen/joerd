from config import make_config_from_argparse
from osgeo import gdal
from importlib import import_module
from multiprocessing import Pool, Array
import joerd.download as download
import joerd.tmpdir as tmpdir
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
from contextlib2 import ExitStack
import subprocess
import ctypes

def create_command_parser(fn):
    def create_parser_fn(parser):
        parser.add_argument('--config', required=True,
                            help='The path to the joerd config file.')
        parser.set_defaults(func=fn)
        return parser
    return create_parser_fn

def _remaining_disk(path):
    df = subprocess.Popen(['df', '-k', '-P', path], stdout=subprocess.PIPE)
    remaining = df.communicate()[0]
    remaining = remaining.split('\n')[1]
    remaining = remaining.split()[3]
    return int(remaining) * 1024

def _make_space(handles, path):
    #assume unpacking will need 3x the space
    needed = 0
    for h in handles:
        position = h.tell();
        h.seek(0, os.SEEK_END)
        needed += h.tell()
        h.seek(position, os.SEEK_SET)
    needed *= 3
    #keep removing stuff until we have enough
    _superfluous.acquire(block=True)
    remaining = _remaining_disk(path)
    for s in _superfluous:
        if remaining >= needed:
            return
        if len(s):
            try:
                gained = os.path.getsize(s)
                os.remove(s)
                remaining += gained
            except:
                pass
            s = ''
    _superfluous.release()
    raise Exception('Not enough space left on device to continue')

def _init_processes(s):
    # in this case its global for each separate process
    global _superfluous
    _superfluous = s

def _download(d):
    try:
        options = d.options().copy()
        options['verifier'] = d.verifier()

        with ExitStack() as stack:
            def _get(u):
                return stack.enter_context(download.get(u, options))

            tmps = [_get(url) for url in d.urls()]

            while True:
                try:
                    d.unpack(*tmps)
                except:
                    _make_space(tmps, os.path.dirname(d.output_file()))

        assert os.path.isfile(d.output_file())

    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


def _render(t, store):
    try:
        with tmpdir.tmpdir() as d:
            t.render(d)
            store.upload_all(d)

    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


def _renderstar(args):
    _render(*args)


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
        self.store = self._store(cfg)

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

        # grab a list of the files which aren't currently available
        need_to_download = []
        need_on_disk = set()
        for download in downloads:
            need_on_disk.add(download.output_file())
            if not os.path.isfile(download.output_file()):
                need_to_download.append(download)

        logger.info("Need to download %d source files."
                    % len(need_to_download))

        #grab a list of the files which we could delete if we need to
        superfluous = []
        for source in self.sources:
            for existing in source.existing_files():
                if existing not in need_on_disk:
                    superfluous.append(existing)

        logger.debug("%d source files are superfluous to this job"
                    % len(superfluous))

        # give each process a handle to the shared mem
        shared = Array(ctypes.c_char_p, superfluous)
        p = Pool(processes=self.num_threads, initializer=_init_processes,
                 initargs=(shared,))

        # make sure we've got a store
        p.map(_download, need_to_download,
              chunksize=self._chunksize(len(need_to_download)))

        logger.info("Starting render of %d tiles." % len(tiles))

        # now render the tiles
        p.map(_renderstar, [(t, self.store) for t in tiles],
              chunksize=self._chunksize(len(tiles)))

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

    def _store(self, cfg):
        store_type = cfg.store['type']
        module = import_module('joerd.store.%s' % store_type)
        create_fn = getattr(module, 'create')
        return create_fn(cfg.store)


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

            # remove the message from the queue - this indicates that it has
            # completed successfully and it won't be retried.
            message.delete()


def joerd_enqueuer(cfg):
    """
    Split the regions in the input file into jobs suitable for enqueueing and
    send them to the SQS queue for the server to work on.
    """

    assert cfg.sqs_queue_name is not None, \
        "Could not find SQS queue name in config, but this must be configured."

    logger = logging.getLogger('enqueuer')
    block_size = cfg.block_size
    bboxes = dict()
    global_region_zoom = None

    for r in cfg.regions.itervalues():
        rbox = r.bbox.bounds
        zrange = r.zoom_range

        # split anything zoom 8 or greater into blocks
        if zrange[1] >= 8:
            lft = int(block_size * math.floor(rbox[0] / block_size))
            bot = int(block_size * math.floor(rbox[1] / block_size))
            rgt = int(block_size * math.ceil(rbox[2] / block_size))
            top = int(block_size * math.ceil(rbox[3] / block_size))

            # just in case, clip to the world
            lft = max(0, lft)
            bot = max(0, bot)
            rgt = min(180, rgt)
            top = min(90, top)

            for x in range(lft, rgt, block_size):
                for y in range(bot, top, block_size):
                    # accumulate the max z for each block
                    zmax = bboxes.get((x, y))
                    bboxes[(x, y)] = max(zmax, zrange[1])

        # for anything with a range < 8, we also do a "global" range
        # starting at the min zoom seen.
        if zrange[0] < 8:
            global_region_zoom = min(global_region_zoom or 8, zrange[0])

    num_jobs = len(bboxes)
    if global_region_zoom is not None:
        num_jobs += 1

    logger.info("Sending %d jobs to the queue" % num_jobs)

    # if there's a global region, then do the whole world down to that
    # zoom.
    if global_region_zoom is not None:
        region = {
            'zoom_range': [global_region_zoom, 8],
            'bbox': {
                'left': -180.0,
                'bottom': -90.0,
                'right': 180.0,
                'top': 90.0,
            }
        }
        sqs.send_message(MessageBody=json.dumps(region))

    # send messages for all the other bboxes that need rendering.
    for (x, y), max_z in bboxes.iteritems():
        region = {
            'zoom_range': [8, max_z],
            'bbox': {
                'left': x,
                'bottom': y,
                'right': x + block_size,
                'top': y + block_size,
            }
        }
        sqs.send_message(MessageBody=json.dumps(region))

    logger.info("Done.")


def joerd_main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = JoerdArgumentParser()
    subparsers = parser.add_subparsers()

    parser_config = (
        ('process', create_command_parser(joerd_process)),
        ('server', create_command_parser(joerd_server)),
        ('enqueuer', create_command_parser(joerd_enqueuer)),
    )

    for name, func in parser_config:
        subparser = subparsers.add_parser(name)
        func(subparser)

    args = parser.parse_args(argv)
    assert os.path.exists(args.config), \
        'Config file %r does not exist.' % args.config
    cfg = make_config_from_argparse(args.config)

    if cfg.logconfig is not None:
        config_dir = os.path.dirname(args.config)
        logconfig_path = os.path.join(config_dir, cfg.logconfig)
        logging.config.fileConfig(logconfig_path)

    args.func(cfg)
