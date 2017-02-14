# Types of Terrain Tiles

The Mapzen terrain tiles provides worldwide basemap coverage sourced from [SRTM](www.openstreetmap.org) and other open data projects with several different data formats, with varying levels of processing.

The following formats are available, full details below:

* `terrarium` with extension `png` in Web Mercator projection, 256x256 tiles
* `normal` with extension `png` in Web Mercator projection, 256x256 tiles
* `geotiff` with extension `tif` in Web Mercator projection, 512x512 tiles
* `skadi` with extension `hgt` in unprojected latlng, 1°x1° tiles

Need help displaying raster tiles in a map? We have several [examples](display-tiles.md) using Mapzen raster tiles to style in your favorite graphics library including Tangram.

## Terrarium

**Terrarium** format _PNG_ tiles contain raw elevation data in meters, in Web Mercator projection (EPSG:3857). All values are positive with a 32,768 offset, split into the red, green, and blue channels, with 16 bits of integer and 8 bits of fraction.

To decode:

  `(red * 256 + green + blue / 256) - 32768`

## Normal

**Normal** format _PNG_ tiles are processed elevation data with the the red, green, and blue values corresponding to the direction the pixel “surface” is facing (its XYZ vector), in Web Mercator projection (EPSG:3857). The alpha channel contains **quantized elevation data** with values suitable for common hypsometric tint ranges.

* `red` = x vector
* `green` = y vector
* `blue` = z vector
* `alpha` = quantized elevation data

High alpha channel values indicate lower elevation values (below sea level), making them more opaque. Specifically, **normal** format alpha values are counted in (floored) elevation increments. Below sea level they start at -11,000 meters (Mariana Trench) and range to -1,000 meters in 1,000 meter increments, with more detail on the coastal shelf at -100, -50, -20, -10 and -1 meters and finally 0 (intertidal zone). Values above sea level are reported in 20 meter increments to 3,000 meters, then 50 meter increments until 6,000 meters, and then 100 meter increments until 8,900 meters (Mount Everest).

Encoding quantized height ranges ([src](https://github.com/tilezen/joerd/blob/master/joerd/output/normal.py#L26-L41)):

```
for i in range(0, 11):
    table.append(-11000 + i * 1000)
table.append(-100)
table.append( -50)
table.append( -20)
table.append( -10)
table.append(  -1)
for i in range(0, 150):
    table.append(20 * i)
for i in range(0, 60):
    table.append(3000 + 50 * i)
for i in range(0, 29):
    table.append(6000 + 100 * i)
```

To decode quantized height value:

  `255 - bisect.bisect_left(HEIGHT_TABLE, h)`

## GeoTIFF

**GeoTIFF** format tiles are raw elevation data suitable for analytical use and are optimized to reduce transfer costs in 512x512 tile sizes but with internal 256x256 image pyramiding, in Web Mercator projection (EPSG:3857). See [GDAL documentation](http://www.gdal.org/frmt_gtiff.html) for more information.

Allow for the larger tile size by referring to the tile coordinate of {z-1} parent tile.

## Skadi

**Skadi** format tiles are raw elevation data in unprojected WGS84 (EPSG:4326) 1°x1° tiles, used by the Mapzen Elevation lookup service. Essentially they are the SRTMGL1 format tiles but with global coverage and compressed using gzip. See [GDAL documentation](http://www.gdal.org/frmt_various.html#SRTMHGT) for more information.

See the [SRTM](https://lpdaac.usgs.gov/sites/default/files/public/measures/docs/NASA_SRTM_V3.pdf) guide for exact format specifications, which are summarized below:

* The DEM is provided as 16-bit signed integer data in a simple binary raster. There are no header or trailer bytes embedded in the file. The data are stored in row major order (all the data for row 1, followed by all the data for row 2, and so on).

* Tiles are compressed in a gzip format and have a '.hgt.gz' type extension.

* All elevations are in meters referenced to the WGS84/EGM96 geoid as documented by the  [National Geospatial Agency](http://earth-info.nga.mil/GandG/wgs84/gravitymod/egm96/egm96.html).

* Byte order is [Motorola ("big-endian") standard](https://en.wikipedia.org/wiki/Endianness) with the most significant byte first. Since they are signed integers elevations can range from -32767 to 32767 meters, encompassing the range of elevation to be found on the Earth.

* These data also contain occasional voids from a number of causes such as shadowing, phase unwrapping anomalies, or other radar-specific causes. Voids are flagged with the value -32768.
