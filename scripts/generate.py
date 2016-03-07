from osgeo import ogr
from yaml import load, dump
from copy import deepcopy
from shapely.wkt import loads
from shapely.geometry import box
import pyqtree
import argparse
import math
import json


# convert OGR readable format to WKT representation
def ogrWkt2Shapely(input_shape):
    # this throws away the other attributes of the feature, but is
    # sufficient in this use case
    shapely_objects=[]
    shp = ogr.Open(input_shape)
    lyr = shp.GetLayer()
    for n in range(0, lyr.GetFeatureCount()):
        feat = lyr.GetFeature(n)
        wkt_feat = loads(feat.geometry().ExportToWkt())
        shapely_objects.append(wkt_feat)
    return shapely_objects


def make_regions(x, y, stride, sub_block_size):
    regions = list()

    # inset the boxes by an epsilon amount. this is so that they don't
    # intersect neighbouring boxes, causing them to be rendered twice.
    # 0.00015 is about 1/7th of a zoom 18 tile (in x direction), so
    # should be large enough to avoid duplication, but small enough to
    # ensure all the tiles we want are actually done, taking into
    # account the overlap between SRTM source tiles.
    epsilon = 0.00015

    # one "top level" region for each skadi tile. this will involve some
    # overlap for the terrarium tiles, sadly.
    for dx in range(0, stride):
        for dy in range(0, stride):
            regions.append(dict(
                bbox=dict(
                    left=(x+dx+epsilon), bottom=(y+dy+epsilon),
                    right=(x+dx+1-epsilon), top=(y+dy+1-epsilon)),
                zoom_range=[8,13]))

    # for each smaller block of tiles, do zooms 14 & 15 too
    sub_block_width = float(stride) / sub_block_size
    for ix in range(0, sub_block_size):
        for iy in range(0, sub_block_size):
            regions.append(dict(
                bbox=dict(
                    left=(x+ix*sub_block_width+epsilon),
                    bottom=(y+iy*sub_block_width+epsilon),
                    right=(x+(ix+1)*sub_block_width-epsilon),
                    top=(y+(iy*1)*sub_block_width-epsilon)),
                zoom_range=[14,16]))

    return regions


def parse_bbox(value):
    bbox = value.split(',')
    if len(bbox) != 4:
        raise argparse.ArgumentError
    return map(float, bbox)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--sub-block-size", help="How many blocks, in "
                        "each direction, to split regions smaller than "
                        "a Skadi tile into.", default=3)
    parser.add_argument("--stride", help="How large is a block? This "
                        "should be no smaller than 1 degree.",
                        default=1)
    parser.add_argument("--bbox", help="Bounding box to limit the extent of "
                        "job creation, expressed as left,bottom,right,top.",
                        default=[-180,-90,180,90], action='store',
                        type=parse_bbox)
    parser.add_argument("--global-region", help="Add a global, low-zoom job "
                        "to the output.", default=False)
    parser.add_argument("--global-mask", help="Add a shape which covers the "
                        "whole input bbox to generate every tile.",
                        default=False)

    parser.add_argument("input-file", help="Config YAML file to read as "
                        "input. Its 'regions' section will be replaced.")
    parser.add_argument("output-file", help="Config jobs list to write. "
                        "This is a file with one job per line, each job is "
                        "a serialised JSON object.")
    parser.add_argument("shape-file", help="Shape file(s) to use. Jobs "
                        "will only be generated where they intersect some "
                        "item from one of these.",
                        nargs='*')

    args = vars(parser.parse_args())

    stride = args['stride']
    sub_block_size = args['sub_block_size']

    bbox = args['bbox']
    bbox[0] = stride * int(math.floor(bbox[0] / stride))
    bbox[1] = stride * int(math.floor(bbox[1] / stride))
    bbox[2] = stride * int(math.ceil(bbox[2] / stride))
    bbox[3] = stride * int(math.ceil(bbox[3] / stride))

    conf = load(open(args['input-file']))

    print "Loading shapefiles..."
    objs = []
    for shapefile in args['shape-file']:
        objs.extend(ogrWkt2Shapely(shapefile))

    if args['global_mask']:
        objs.append(box(*bbox))

    print "Building index..."
    index = pyqtree.Index(bbox=[-180,-90,180,90])
    for o in objs:
        index.insert(item=o, bbox=o.bounds)

    regions = list()
    hit = 0
    total = 0

    if args['global_region']:
        regions.append(dict(
            bbox=dict(
                left=-180,
                bottom=-90,
                right=180,
                top=90),
            zoom_range=[0,8]))

    print "Intersecting inside bbox %r..." % bbox
    for x in range(bbox[0], bbox[2], stride):
        if total > 0:
            print "   >> x = %d (%d/%d = %.1f%%)" \
                % (x, hit, total, (100.0 * hit) / total)

        for y in range(bbox[1], bbox[3], stride):
            bb = [x, y, x + stride, y + stride]
            b = box(*bb)
            for o in index.intersect(bb):
                if b.intersects(o):
                    regions.extend(make_regions(x, y, stride,
                                                sub_block_size))
                    hit += 1
                    break
            total += 1

    print "Done, writing new config."
    with open(args['output-file'], 'w') as fh:
        for r in regions:
            fh.write(json.dumps(r) + "\n")
