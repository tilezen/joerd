#Mapzen Terrain Tiles

The [Mapzen terrain tiles](https://mapzen.com/projects/joerd) provides worldwide basemap coverage sourced from several open data projects.

![Contents of an example terrain tile](images/elevation-tile-example.png)

Raster tiles are square-shaped grids of geographic data that contain contain either raw elevation data or processed data (like normals).

Tiles are available at zooms 0 through 15 and are available in several formats including PNG and GeoTIFF, and raw elevation and processed normal values optimized for mobile and web display, and desktop analytical use. Data is available in both web Mercator projected and raw latlng.

With terrain tiles you have the power to customize the content and visual appearance of the map and perform analysis on the desktop. We're excited to see what you build!

### Use Mapzen's Terrain Tiles

To start integrating vector tiles to your app, you need a [developer API key](https://mapzen.com/developers). API keys come in the pattern: `vector-tiles-xxxxxxx`.

* [API keys and rate limits](api-keys-and-rate-limits.md) - Don't abuse the shared service!
* [Attribution requirements](attribution.md) - Terms of service for open data projects require attribution.

#### Requesting tiles

The URL endpoint pattern to request tiles is:

- `https://tile.mapzen.com/{format}/v1/{z}/{x}/{y}.{extension}?api_key=terrain-tiles-xxxxxxx`

Where format is one of:

* `terrarium` with extention `png`
* `normal` with extention `png`
* `geotiff` with extention `tif`
* `skadi` with extention `hgt`

Here’s a sample Terrarium in PNG format:

- `https://tile.mapzen.com/terrarium/v1/0/0/0.png?api_key=terrain-tiles-xxxxxxx`

More information is available about how to [use the terrain tile service](use-service.md).

#### File formats

* **Terrarium** format _PNG_ tiles provide raw elevation values in web Mercator projection.
* **Normal** format _PNG_ tiles provide processed elevation values with the the red, green, and blue values corresponding to the direction the pixel “surface” is facing (its XYZ vector), in Mercator projection, and alpha channel contains **quantized elevation data** with values suitable for common hypsometric tint ranges
* **GeoTIFF** format tiles provide raw elevation values in web Mercator projection but with 512x512 sized tiles.
* **Skadi** format tiles are raw elevation data in unprojected latlng 1°x1° tiles, used by the Mapzen Terrain Service.

More information is available about [file formats](formats.md).

#### Data sources

Mapzen aggregates elevation data from several open data providers including:

- 3 meter and 10 meter [3DEP](http://nationalmap.gov/elevation.html) in the United States (formerly NED)
- 30 meter [SRTM](https://lta.cr.usgs.gov/SRTM) globally
- coarser [GMTED2010](http://topotools.cr.usgs.gov/gmted_viewer/) zoomed out
- [ETOPO1](https://www.ngdc.noaa.gov/mgg/global/global.html) to fill in bathymetry

More information is available about [data sources](data-sources.md).

**Could we provide better coverage in your area?** Please recommend additional open datasets to include by [filing an issue](https://github.com/tilezen/joerd/issues/new).

#### Related service

To query elevation at a single point or along a path almost anywhere in the globe, [sign up for an API key](https://mapzen.com/developers/) and check out the [Mapzen Elevation Service](https://mapzen.com/documentation/elevation/).

##### Building a map

How to [draw the tile](build-a-map.md#tangram) in a browser is up to the raster-friendly visualization tool, such as WebGL. The [Tangram](https://mapzen.com/projects/tangram) rendering engine is one way that you can draw the raster tiles in 2D and 3D maps.

More interested in analytical tools on the desktop or in the cloud? We walk you thru how to download & merge tiles and generate hillshades using [GDAL](build-a-map.md#gdal) and [QGIS](build-a-map.md#qgis).

### How are raster terrain tiles produced?

Terrain tiles are served by clipping source grids to the tile bounding box and tile downsampling resolution to match the zoom level to avoid unnecessary complexity at lower zoom levels. Ground resolution table is available in the [data sources](data-sources.md#what-is-the-ground-resolution) description.

### Build from source

If you are interested in setting up your own version of this service, follow these [installation instructions](https://github.com/tilezen/joerd#building).

### Credits

Many thanks to Amazon for providing EC2 and S3 resources for processing and distributing v1 terrain tiles as part of their public data initiative!

### Additional resources

Mapzen blog post and other resources:

- [What a Relief: Global Test Pilots Wanted](https://mapzen.com/blog/elevation/)
- [Mapping Mountains](https://mapzen.com/blog/mapping-mountains/)
- [Moving on up! (using Mapzen's Elevation Service)](https://mapzen.com/blog/moving-on-up/)