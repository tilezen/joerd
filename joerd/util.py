class BoundingBox:
    def __init__(self, left, bottom, right, top):
        self.bounds = (left, bottom, right, top)

    def __eq__(a, b):
        return isinstance(b, type(a)) and \
            a.bounds == b.bounds

    def __hash__(self):
        return hash(self.bounds)

    def intersects(self, other):
        if self.bounds[0] > other.bounds[2]:
            return False
        if self.bounds[1] > other.bounds[3]:
            return False
        if self.bounds[2] < other.bounds[0]:
            return False
        if self.bounds[3] < other.bounds[1]:
            return False
        return True

    def buffer(self, size):
        return BoundingBox(
            self.bounds[0] - size,
            self.bounds[1] - size,
            self.bounds[2] + size,
            self.bounds[3] + size)
