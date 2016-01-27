import unittest
from joerd.util import BoundingBox


class TestBoundingBox(unittest.TestCase):

    def test_intersection(self):
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(0, 0, 1, 1)))

        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(1, 0, 2, 1)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(1, 1, 2, 2)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(0, 1, 1, 2)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-1, 1, 0, 2)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-1, 0, 0, 1)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-1, -1, 0, 0)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(0, -1, 1, 0)))
        self.assertTrue(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(1, -1, 2, 0)))

        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(2, 2, 3, 3)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(0, 2, 1, 3)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-2, 2, -1, 3)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-2, 0, -1, 1)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(-2, -2, -1, -1)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(0, -2, 1, -1)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(2, -2, 3, -1)))
        self.assertFalse(
            BoundingBox(0, 0, 1, 1).intersects(BoundingBox(2, 0, 3, 1)))
