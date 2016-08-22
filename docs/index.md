#Mapzen Elevation Tiles

The [Mapzen elevation tiles](https://mapzen.com/projects/elevation-tiles) provides worldwide basemap coverage sourced from several open data projects.

![Contents of an example elevation tile](images/elevation-tile-example.png)

Raster tiles are square-shaped grids of geographic data that contain contain either raw elevation data or processed data (like normals).

Tiles are available at zooms 0 through 15 and are available in several formats including PNG and GeoTIFF, and raw elevation and processed normal values optimized for mobile and web display, and desktop analytical use. Data is available in both web Mercator projected and raw latlng.

With elevation tiles you have the power to customize the content and visual appearance of the map and perform analysis on the desktop. We're excited to see what you build!

#### File formats

* **Terrarium** format _PNG_ tiles provide raw elevation values in web Mercator projection.
* **GeoTIFF** format tiles provide raw elevation values in web Mercator projection.
* **Normal** format _PNG_ tiles provide processed elevation values with the the red, green, and blue values corresponding to the direction the pixel “surface” is facing (its XYZ vector), in Mercator projection, and alpha channel contains **quantized elevation data** with values suitable for common hypsometric tint ranges
* **Skadi** format tiles are raw elevation data in unprojected latlng 1°x1° tiles, used by the Mapzen Elevation Service.

### Use Mapzen's Elevation Tiles

To start integrating vector tiles to your app, you need a [developer API key](https://mapzen.com/developers). API keys come in the pattern: `vector-tiles-xxxxxxx`.

* [API keys and rate limits](api-keys-and-rate-limits.md) - Don't abuse the shared service!
* [Attribution requirements](attribution.md) - Terms of service for open data projects require attribution.

#### Requesting tiles

The URL endpoint pattern to request tiles is:

- `https://tile.mapzen.com/{format}/v1/{z}/{x}/{y}.{extension}?api_key=elevation-tiles-xxxxxxx`

Where format is one of:

* `terrarium` with extention `png`
* `geotiff` with extention `tif`
* `normal` with extention `png`
* `skadi` with extention `hgt`

Here’s a sample Terrarium in PNG format:

- `https://tile.mapzen.com/terrarium/v1/0/0/0.png?api_key=elevation-tiles-xxxxxxx`

More information is available about how to [use the elevation tile service](use-service.md).

#### Data sources

Mapzen aggregates elevation data from several open data providers including:

- 3 meter and 10 meter [3DEP](http://nationalmap.gov/elevation.html) in the United States (formerly NED)
- 30 meter [SRTM](https://lta.cr.usgs.gov/SRTM) globally
- coarser [GMTED2010](http://topotools.cr.usgs.gov/gmted_viewer/) zoomed out
- [ETOPO1](https://www.ngdc.noaa.gov/mgg/global/global.html) to fill in bathymetry

**Could we provide better coverage in your area?** Please recommend additional open datasets to include by [filing an issue](https://github.com/tilezen/joerd/issues/new).

#### Related service

To query elevation at a single point or along a path almost anywhere in the globe, [sign up for an API key](https://mapzen.com/developers/) and check out the [Mapzen Elevation Service](https://mapzen.com/documentation/elevation/).

##### Drawing a map

How to [draw the tile](display-tiles.md) in a browser is up to the raster-friendly visualization tool, such as WebGL. The [Tangram](https://mapzen.com/projects/tangram) rendering engine is one way that you can draw the raster tiles in 2D and 3D maps.

#### How are raster elevation tiles produced?

Elevation tiles are served by clipping source grids to the tile bounding box and tile downsampling resolution to match the zoom level to avoid unnecessary complexity at lower zoom levels. Ground resolution table is available in the [data sources]() description.

#### Build from source

If you are interested in setting up your own version of this service, follow these [installation instructions](https://github.com/tilezen/joerd#building).

#### See also:

- [What a Relief: Global Test Pilots Wanted](https://mapzen.com/blog/elevation/)
- [Mapping Mountains](https://mapzen.com/blog/mapping-mountains/)
- [Moving on up! (using Mapzen's Elevation Service)](https://mapzen.com/blog/moving-on-up/)