import traceback
import json
import sys


class Dispatcher(object):
    """
    Convenience class to handle queueing up a batch of jobs to the queue
    and pushing or flushing them when necessary. It also catches and
    ignores errors.
    """

    def __init__(self, queue, max_batch_len, logger):
        self.queue = queue
        self.max_batch_len = max_batch_len
        self.logger = logger

        self.batch = self.queue.start_batch(self.max_batch_len)
        self.idx = 0
        self.next_log_idx = 0

    def append(self, job):
        try:
            self.batch.append(job)
        except StandardError as e:
            self.logger.warning("Failed to enqueue batch: %s" \
                                % "".join(traceback.format_exception(
                                    *sys.exc_info())))

        self.idx += 1
        if self.idx >= self.next_log_idx:
            self.logger.info("Dispatched %d jobs" % self.idx)
            self.next_log_idx += 1000

    def flush(self):
        try:
            self.batch.flush()
        except StandardError as e:
            self.logger.warning("Failed to flush batch: %s" \
                                % "".join(traceback.format_exception(
                                    *sys.exc_info())))

        self.logger.info("Dispatcher sent %d jobs in total." % self.idx)


class JSONSizer(object):
    def __init__(self, sources, limit):
        self.limit = limit
        self.data = []
        self.size = 0
        fake_job_data = self._job_data(sources)
        self.initial_size = len(json.dumps(fake_job_data))

    def _job_data(self, sources):
        return dict(job='renderbatch',
                    sources=sources,
                    data=self.data)

    def append(self, sources, data):
        flushed = None
        data_size = len(json.dumps(data)) + 1

        assert data_size < self.limit, "Job too large for limit: " \
            "%d >= %d." % (self.size + 1, self.limit)

        if data_size + self.size > self.limit:
            flushed = self.flush(sources)

        self.data.append(data)
        self.size += data_size + 1

        return flushed

    def flush(self, sources):
        flushed = self._job_data(sources)
        self.data = []
        self.size = self.initial_size
        return flushed


def _freeze(obj):
    if isinstance(obj, dict):
        frozen_items = [(_freeze(k), _freeze(v)) for (k, v) in obj.items()]
        return frozenset(frozen_items)

    elif isinstance(obj, list):
        return tuple([_freeze(item) for item in obj])

    else:
        return obj


def _thaw(obj):
    if isinstance(obj, frozenset):
        thawed_items = [(_thaw(k), _thaw(v)) for (k, v) in obj]
        return dict(thawed_items)

    elif isinstance(obj, tuple):
        return list([_thaw(item) for item in obj])

    else:
        return obj


class GroupingDispatcher(object):
    """
    A dispatcher which groups jobs by the sources that they require. This
    should help to improve cache re-use.
    """

    def __init__(self, queue, max_batch_len, logger, size_limit):
        self.queue = queue
        self.max_batch_len = max_batch_len
        self.logger = logger
        self.limit = size_limit

        self.batches = {}
        self.dispatcher = Dispatcher(self.queue, self.max_batch_len,
                                     self.logger)

    def append(self, job):
        job_typ = job.get('job')
        sources = job.get('sources')

        if sources and job_typ == 'render':
            self._append_render_batch(sources, job['data'])

        else:
            self.dispatcher.append(job)

    def _append_render_batch(self, sources, data):
        sources_key = _freeze(sources)
        json_sizer = self.batches.get(sources_key)

        if json_sizer is None:
            json_sizer = JSONSizer(sources, self.limit)
            self.batches[sources_key] = json_sizer

        flushed = json_sizer.append(sources, data)
        if flushed:
            self.dispatcher.append(flushed)

    def flush(self):
        for sources_key, json_sizer in self.batches.iteritems():
            flushed = json_sizer.flush(_thaw(sources_key))
            self.dispatcher.append(flushed)

        self.dispatcher.flush()
