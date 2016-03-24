from joerd.mkdir_p import mkdir_p
import joerd.tmpdir as tmpdir
import joerd.download as download
from joerd.plugin import plugin
from contextlib2 import ExitStack, contextmanager
import logging
import traceback
import os.path
import sys


def _download(d, store):
    """
    Download a source file from the internet and store it in the given store.
    """

    logger = logging.getLogger('download')

    try:
        options = download.options(d.options()).copy()
        options['verifier'] = d.verifier()

        with ExitStack() as stack:
            def _get(u):
                return stack.enter_context(download.get(u, options))

            tmps = [_get(url) for url in d.urls()]

            try:
                d.unpack(store, *tmps)

            except Exception as e:
                logger.error(repr(e))
                raise Exception("Failed to download %r: %s" %
                                (d.output_file(),
                                 "".join(traceback.format_exception(
                                     *sys.exc_info()))))

        assert store.exists(d.output_file())

    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


def _download_local_vrts(d, source_store, input_vrts):
    """
    The input VRTs are stored in the source_store, but GDAL doesn't know about
    any store other than the filesystem. This function downloads all the files
    referenced in the VRTs to a local, temporary directory and rewrites the
    vrts to include the local paths instead of the remote ones.

    It returns the list of list of rewritten VRT paths.
    """

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


def _render(t, store):
    """
    Renders a tile, sending output to a temporary directory and puts the
    result(s) in the store.
    """

    try:
        with tmpdir.tmpdir() as d:
            t.render(d)
            store.upload_all(d)

    except:
        raise Exception("".join(traceback.format_exception(*sys.exc_info())))


class MockSource(object):
    """
    Used to wrap a source and override its `vrts_for` method so that VRTs which
    have been downloaded from a source store to the local filesystem can be
    used.
    """

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


class Server:
    """
    Joerd "server" or worker class. It can list the downloads required for a
    configured region or run a job. Jobs can be either downloads of a single
    source file or renders of a single output tile.
    """

    def __init__(self, cfg):
        self.regions = cfg.regions
        self.sources = self._sources(cfg)
        self.outputs = self._outputs(cfg, self.sources)
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
            create_fn = plugin('source', source_type, 'create')
            sources.append((source_type, create_fn(source)))
        return sources

    def _outputs(self, cfg, sources):
        outputs = {}
        for output in cfg.outputs:
            output_type = output['type']
            create_fn = plugin('output', output_type, 'create')
            outputs[output_type] = create_fn(cfg.regions, sources, output)
        return outputs

    def _store(self, store_cfg):
        store_type = store_cfg['type']
        create_fn = plugin('store', store_type, 'create')
        return create_fn(store_cfg)

    def _find_source_by_name(self, name):
        for n, source in self.sources:
            if n == name:
                return source
        raise Exception("Unable to find source called %r" % name)

    def _download(self, rehydrated):
        _download(rehydrated, self.source_store)

    def _render(self, rehydrated, sources):
        with tmpdir.tmpdir() as d:
            mock_sources = []
            for s in sources:
                src = self._find_source_by_name(s['source'])
                vrts = _download_local_vrts(d, self.source_store, s['vrts'])
                if vrts:
                    mock_sources.append(MockSource(src, vrts))

            rehydrated.set_sources(mock_sources)

            _render(rehydrated, self.store)

    def _run_job_download(self, job):
        data = job['data']
        typ = data['type']
        src = self._find_source_by_name(typ)
        rehydrated = src.rehydrate(data)
        self._download(rehydrated)

    def _run_job_render(self, job):
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

        rehydrated = self.outputs[typ].rehydrate(data)
        self._render(rehydrated, sources)

    def dispatch_job(self, job):
        logger = logging.getLogger('process')

        job_type = job.get('job')

        if job_type == 'download':
            self._run_job_download(job)

        elif job_type == 'render':
            self._run_job_render(job)

        else:
            raise Exception("Don't understand job type %r from job %r, " \
                            "ignoring." % (job_type, job))
