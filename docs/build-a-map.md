# Building a map with Mapzen terrain tiles

You can use Mapzen’s terrain tiles with a variety of browser-based rendering software packages. Following the syntax of the library you are using, you need to specify the URL to the Mapzen terrain tile service, the layers that you want to draw on the map, and styling information about how to draw the features.

## Tangram

[Tangram](https://mapzen.com/projects/tangram) is a WebGL browser based mapping engine and supports native iOS and Android rendering with OpenGL in 2D and 3D from vector and raster tiles.

* **Walkabout demo:** [preview](http://tangrams.github.io/walkabout-style-more-labels) | [source code](http://github.com/tangrams/walkabout-style-more-labels)

![image](https://cloud.githubusercontent.com/assets/853051/11137284/13e3a5f0-896b-11e5-9ab9-be51ecb388d8.png)

## GDAL

GDAL allows Desktop analytics, hill shading, and contouring.

The [collect.py](https://github.com/tilezen/joerd/blob/master/docs/examples/collect.py) script in the examples downloads GeoTIFF tiles in a bounding box and optionally merges them into one big file.

Once you have that big file, you could run [gdaldem hillshade](http://www.gdal.org/gdaldem.html#gdaldem_hillshade) to generate a basic hillshade. Mapbox has a great [tutorial](https://www.mapbox.com/tilemill/docs/guides/terrain-data/#creating-hillshades) with full set of options.

## QGIS

