class BoundingBox:
    def __init__(self, left, bottom, right, top):
        self.bounds = (left, bottom, right, top)

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
