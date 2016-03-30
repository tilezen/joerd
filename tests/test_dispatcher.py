import unittest
import joerd.dispatcher as dispatcher
import sys


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
