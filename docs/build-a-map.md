# Building a map with Mapzen elevation tiles

You can use Mapzen’s elevation tiles with a variety of browser-based rendering software packages. Following the syntax of the library you are using, you need to specify the URL to the Mapzen elevation tile service, the layers that you want to draw on the map, and styling information about how to draw the features.

## Tangram

[Tangram](https://mapzen.com/projects/tangram) is a WebGL browser based mapping engine and supports native iOS and Android rendering with OpenGL in 2D and 3D from vector and raster tiles.

* **Walkabout demo:** [preview](http://tangrams.github.io/walkabout-style-more-labels) | [source code](http://github.com/tangrams/walkabout-style-more-labels)

![image](https://cloud.githubusercontent.com/assets/853051/11137284/13e3a5f0-896b-11e5-9ab9-be51ecb388d8.png)

## GDAL

GDAL allows Desktop analytics, hill shading, and contouring.

_TODO: script needs to be writen to download tiles in a given area and hillshade them, show result in QGIS_

_See:_

- http://jgomezdans.github.io/stitching-together-modis-data.html
- https://gist.github.com/jgomezdans/3152468
- http://www.mikejcorey.com/wordpress/2011/02/05/tutorial-create-beautiful-hillshade-maps-from-digital-elevation-models-with-gdal-and-mapnik/
- https://www.mapbox.com/tilemill/docs/guides/terrain-data/#creating-hillshades
- http://www.gdal.org/gdal_merge.html

## QGIS

