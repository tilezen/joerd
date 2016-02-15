import pyqtree
import yaml
import logging
import thread


# Create an index given a YAML file consisting of a list of strings and a
# function to parse it. Extra, fixed arguments for the function can be also
# be given. Each object returned from the `parse_fn` should have a member
# called `bbox` which is a `joerd.util.BoundingBox` instance.
def create(index_file, bbox, parse_fn, *parse_args):
    logger = logging.getLogger("index")
    idx = pyqtree.Index(bbox=bbox)
    n = 0

    with open(index_file, 'r') as f:
        files = yaml.load(f.read())
        for f in files:
            t = parse_fn(f, *parse_args)
            if t:
                idx.insert(bbox=t.bbox.bounds, item=t)
                n += 1

    logger.info("Created index with %d objects." % n)
    return idx


# Returns a list of all objects intersecting the given bbox in the index.
def intersections(idx, bbox):
    return idx.intersect(bbox.bounds)
