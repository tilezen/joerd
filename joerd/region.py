class Region(object):
    """
    Represents a selection of space and a range of scales at which to render.
    Any output tiles which intersect this should be rendered.

    The choice of zoom as a scale is partly because it's simpler than some
    other scale, and partly becase Mercator output is expected to be the
    majority of the tiles rendered. Other projections should calculate the
    scale against longitude for consistency.

    Note that the zoom range is *exclusive* of the max zoom.
    """

    def __init__(self, bbox, zoom_range):
        self.bbox = bbox
        self.zoom_range = zoom_range

    def intersects(self, bbox, zoom):
        return self.bbox.intersects(bbox) and \
            zoom >= self.zoom_range[0] and \
            zoom < self.zoom_range[1]
