import unittest
import joerd.output.terrarium as terrarium
from joerd.region import Region
from joerd.util import BoundingBox
import joerd.dispatcher as dispatcher
import sys
import logging


class TestDispatcher(unittest.TestCase):

    def test_freeze(self):
        examples = [
            {},
            [],
            1,
            'a',
            [[]],
            {'a':{}},
            {'source': 'ned13', 'vrts': [['ned13/imgn38w123_13.img']]}
        ]

        for example in examples:
            k = dispatcher._freeze(example)

            # this will throw if k isn't immutable
            d = dict()
            d[k] = None

            # check that the thawed value is the same as the original
            value = dispatcher._thaw(k)
            self.assertEqual(example, value)

    def test_dispatch_tiles(self):
        regions = [
            Region(BoundingBox(-124.56, 32.4, -114.15, 42.03), [8, 10])
        ]
        t = terrarium.Terrarium(regions, [])

        class Batch(object):
            def __init__(self, queue, max_batch_len):
                self.queue = queue
                self.batch = []

            def append(self, job):
                self.batch.append(job)

            def flush(self):
                for job in self.batch:
                    self.queue.append(job)
                self.batch = []

        class Queue(object):
            def __init__(self):
                self.expected = set([
                    (8, 41, 99),
                    (8, 43, 98)
                ])

            def start_batch(self, max_batch_len):
                return Batch(self, max_batch_len)

            def append(self, tile):
                coord = (tile.z, tile.x, tile.y)
                if coord in self.expected:
                    self.expected.remove(coord)

            def flush(self):
                pass

        logger = logging.getLogger('process')
        queue = Queue()
        d = dispatcher.Dispatcher(queue, 10, logger)

        for tile in t.generate_tiles():
            d.append(tile)

        d.flush()
        self.assertEqual(queue.expected, set([]))

    def test_group_dispatch_tiles(self):
        regions = [
            Region(BoundingBox(-124.56, 32.4, -114.15, 42.03), [8, 10])
        ]
        t = terrarium.Terrarium(regions, [])

        class Batch(object):
            def __init__(self, queue, max_batch_len):
                self.queue = queue
                self.batch = []

            def append(self, job):
                self.batch.append(job)

            def flush(self):
                for job in self.batch:
                    self.queue.append(job)
                self.batch = []

        class Queue(object):
            def __init__(self):
                self.expected = set([
                    (8, 41, 99),
                    (8, 43, 98)
                ])

            def start_batch(self, max_batch_len):
                return Batch(self, max_batch_len)

            def append(self, tile):
                coord = (tile['z'], tile['x'], tile['y'])
                if coord in self.expected:
                    self.expected.remove(coord)

            def flush(self):
                pass

        class FakeLogger(object):
            def info(self, msg):
                print msg

            def warning(self, msg):
                print msg

        logger = FakeLogger()
        queue = Queue()
        d = dispatcher.GroupingDispatcher(queue, 10, logger, 1000)

        for tile in t.generate_tiles():
            d.append(tile.freeze_dry())

        d.flush()
        self.assertEqual(queue.expected, set([]))
