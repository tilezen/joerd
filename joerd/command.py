from config import make_config_from_argparse
from osgeo import gdal
from importlib import import_module
from multiprocessing import Pool, Array
import joerd.download as download
import joerd.tmpdir as tmpdir
from joerd.region import RegionTile
from joerd.mkdir_p import mkdir_p
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
from contextlib2 import ExitStack, contextmanager
import subprocess
import ctypes
import math


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

def _remaining_disk(path):
    df = subprocess.Popen(['df', '-k', '-P', path], stdout=subprocess.PIPE)
    remaining = df.communicate()[0]
    remaining = remaining.split('\n')[1]
    remaining = remaining.split()[3]
    return int(remaining) * 1024

@contextmanager
def lock_array(a, **opts):
    a.acquire(**opts)
    try:
        yield a
    finally:
        a.release()

def _make_space(tmps, path):
    #if theres nothing to do bail
    with lock_array(_superfluous, block=True) as superfluous:
        if len(superfluous) and not superfluous[len(superfluous) - 1]:
            raise Exception('Need more space but nothing superfluous to delete.')
        #assume unpacking will need at least this much space
        needed = 0
        for t in tmps:
            needed += os.path.getsize(t.name)
        #keep removing stuff until we have enough
        remaining = _remaining_disk(path)
        for i in range(len(superfluous)):
            if remaining >= needed:
                return
            s = superfluous[i]
            superfluous[i] = ''
            if s:
                try:
                    _logger.info('Removing %s to free up space.' % s)
                    gained = os.path.getsize(s)
                    os.remove(s)
                    remaining += gained
                except:
                    pass
    #still not enough
    if remaining < needed:
        raise Exception('Not enough space left on device to continue, need at least %d more bytes.' % (needed - remaining))

def _init_processes(s, l):
    # in this case its global for each separate process
    global _superfluous
    _superfluous = s
    global _logger
    _logger = l

    # make sure process will error if GDAL fails
    gdal.UseExceptions()


def _download(d, store):
    logger = logging.getLogger('download')

    try:
        options = download.options(d.options()).copy()
        options['verifier'] = d.verifier()

        with ExitStack() as stack:
            def _get(u):
                return stack.enter_context(download.get(u, options))

            tmps = [_get(url) for url in d.urls()]

            while True:
                try:
                    d.unpack(store, *tmps)
                    break
                except Exception as e:
                    #TODO: only catch out of space exception
                    logger.error(repr(e))
                    # disable attempt to make space for now - the code changes
                    # make it non-functional.
                    #_make_space(tmps, os.path.dirname(d.output_file()))

        assert store.exists(d.output_file())

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
        self.regions = cfg.regions
        self.sources = self._sources(cfg)
        self.outputs = self._outputs(cfg, self.sources)
        self.num_threads = cfg.num_threads
        self.chunksize = cfg.chunksize
        self.store = self._store(cfg.store)
        self.source_store = self._store(cfg.source_store)

    def list_downloads(self):
        logger = logging.getLogger('process')

        # fetch index for each source, which speeds up subsequent downloads or
        # queries about which source tiles are available.
        for name, source in self.sources:
            source.get_index()

        # take the list of regions, which are both spatial and zoom extents,
        # and expand them for each output, making them concrete resolutions
        # and spatial extents enough to cover the output tiles.
        expanded_regions = list()
        for r in self.regions:
            bbox = r.bbox.bounds
            for output in self.outputs.itervalues():
                expanded_regions.extend(output.expand_tile(bbox, r.zoom_range))

        # the list of expanded regions can now be intersected with each source
        # to find the ones which intersect, and give the set of download jobs.
        downloads = set()
        for tile in expanded_regions:
            for name, source in self.sources:
                d = source.downloads_for(tile)
                if d:
                    downloads.update(d)

        return downloads

    def _sources(self, cfg):
        sources = []
        for source in cfg.sources:
            source_type = source['type']
            module = import_module('joerd.source.%s' % source_type)
            create_fn = getattr(module, 'create')
            sources.append((source_type, create_fn(source)))
        return sources

    def _outputs(self, cfg, sources):
        outputs = {}
        for output in cfg.outputs:
            output_type = output['type']
            module = import_module('joerd.output.%s' % output_type)
            create_fn = getattr(module, 'create')
            outputs[output_type] = create_fn(cfg.regions, sources, output)
        return outputs

    def _store(self, store_cfg):
        store_type = store_cfg['type']
        module = import_module('joerd.store.%s' % store_type)
        create_fn = getattr(module, 'create')
        return create_fn(store_cfg)


class JoerdArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def _find_source_by_name(j, name):
    for n, source in j.sources:
        if n == name:
            return source
    raise Exception("Unable to find source called %r" % name)


def _run_job_download(j, job):
    data = job['data']
    typ = data['type']
    src = _find_source_by_name(j, typ)
    rehydrated = src.rehydrate(data)
    _download(rehydrated, j.source_store)


class MockSource(object):
    def __init__(self, src, vrts):
        self.src = src
        self.vrts = vrts

    def __getattr__(self, method_name):
        def return_vrts(self, tile):
            return self.vrts

        if method_name == 'vrts_for':
            return return_vrts.__get__(self)
        else:
            return self.src.__getattribute__(method_name)


def _download_local_vrts(d, source_store, input_vrts):
    vrts = []
    for rasters in input_vrts:
        v = []
        for r in rasters:
            filename = os.path.join(d, r)
            mkdir_p(os.path.dirname(filename))
            source_store.get(r, filename)
            assert os.path.exists(filename), "Tried to get %r from " \
                "store and store it to %r, but that doesn't seem to " \
                "have worked." % (r, filename)
            v.append(filename)
        if v:
            vrts.append(v)

    return vrts


def _run_job_render(j, job):
    logger = logging.getLogger('process')

    data = job['data']
    typ = data['type']

    # composite operation needs to look up the sources, so we
    # need to wrap each source in a fake source which overrides
    # the 'vrts_for' lookup with the sources we baked into the
    # job.
    sources = job.get('sources')
    assert sources, "Got tile render job with no sources! Job was: " \
        "%r" % job

    rehydrated = j.outputs[typ].rehydrate(data)

    with tmpdir.tmpdir() as d:
        mock_sources = []
        for s in sources:
            src = _find_source_by_name(j, s['source'])
            vrts = _download_local_vrts(d, j.source_store, s['vrts'])
            if vrts:
                mock_sources.append(MockSource(src, vrts))

        rehydrated.set_sources(mock_sources)

        _render(rehydrated, j.store)


def _dispatch_job(j, message_body):
    job = json.loads(message_body)
    job_type = job.get('job')

    if job_type == 'download':
        _run_job_download(j, job)

    elif job_type == 'render':
        _run_job_render(j, job)

    else:
        raise Exception("Don't understand job type %r from job %r, " \
                        "ignoring." % (job_type, job))


def joerd_server(global_cfg):
    logger = logging.getLogger('process')

    assert global_cfg.sqs_queue_name is not None, \
        "Could not find SQS queue name in config, but this must be configured."

    j = Joerd(global_cfg)
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=global_cfg.sqs_queue_name)

    while True:
        for message in queue.receive_messages():
            try:
                _dispatch_job(j, message.body)

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


def joerd_enqueuer(cfg):
    """
    Sends each region in the config file to the queue for processing by workers.
    """

    assert cfg.sqs_queue_name is not None, \
        "Could not find SQS queue name in config, but this must be configured."

    logger = logging.getLogger('enqueuer')

    j = Joerd(cfg)

    logger.info("Streaming jobs to the queue")
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=cfg.sqs_queue_name)

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
            batch.append(dict(Id=str(idx), MessageBody=json.dumps(job)))
            idx += 1

            if len(batch) == 10:
                result = queue.send_messages(Entries=batch)
                if 'Failed' in result and result['Failed']:
                    logger.warning("Failed to enqueue: %r" % result['Failed'])
                batch = []

            if idx >= next_log_idx:
                logger.info("Sent %d jobs to queue." % idx)
                next_log_idx += 1000

    if len(batch) > 0:
        result = queue.send_messages(Entries=batch)
        if 'Failed' in result and result['Failed']:
            logger.warning("Failed to enqueue: %r" % result['Failed'])

    logger.info("Done.")


def joerd_enqueue_downloads(cfg):
    """
    Sends a list of all the source files needed for rendering the configured
    regions in the config file to the queue for downloading by workers.
    """

    assert cfg.sqs_queue_name is not None, \
        "Could not find SQS queue name in config, but this must be configured."

    logger = logging.getLogger('enqueuer')

    j = Joerd(cfg)
    downloads = j.list_downloads()

    logger.info("Sending %d download jobs to the queue" % len(downloads))
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=cfg.sqs_queue_name)

    batch = []
    idx = 0

    for d in downloads:
        data = d.freeze_dry()
        job = dict(job='download', data=data)
        batch.append(dict(Id=str(idx), MessageBody=json.dumps(job)))
        idx += 1

        if len(batch) == 10:
            result = queue.send_messages(Entries=batch)
            if 'Failed' in result and result['Failed']:
                logger.warning("Failed to enqueue: %r" % result['Failed'])
            batch = []

    if len(batch) > 0:
        result = queue.send_messages(Entries=batch)
        if 'Failed' in result and result['Failed']:
            logger.warning("Failed to enqueue: %r" % result['Failed'])

    logger.info("Done.")


def joerd_main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = JoerdArgumentParser()
    subparsers = parser.add_subparsers()

    parser_config = (
        ('server', create_command_parser(joerd_server)),
        ('enqueuer', create_command_parser(joerd_enqueuer)),
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
