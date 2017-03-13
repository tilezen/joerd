# Get started with Mapzen Terrain Tiles

The Mapzen terrain tiles provide basemap elevation coverage of the world in a raster tile format. Tiles are available for zooms 0 through 15 and are available in several spatial data formats including PNG and GeoTIFF. The tiles also can be in a raw elevation and processed normal value format that's optimized for mobile and web display, and desktop analytical use. Data is available in both Web Mercator (EPSG:3857) projected and raw latlng. Learn more about the [various data formats](fileformats.md) offered.

## Get an API key

To start integrating terrain tiles to your project you need a [developer API key](https://mapzen.com/documentation/overview/).

## Requesting tiles

You can request tiles using Mapzen's global CDN:

##### Terrarium

  `https://tile.mapzen.com/mapzen/terrain/v1/terrarium/{z}/{x}/{y}.png`

##### Normal

  `https://tile.mapzen.com/mapzen/terrain/v1/normal/{z}/{x}/{y}.png`

##### GeoTIFF

  `https://tile.mapzen.com/mapzen/terrain/v1/geotiff/{z}/{x}/{y}.tif`

  Note: GeoTIFF format tiles are 512x512 sized so request the parent tile’s coordinate. For instance, if you’re looking for a zoom 14 tile then request the parent tile at zoom 13.

##### Skadi

  `https://tile.mapzen.com/mapzen/terrain/v1/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`
  
  Note: Skadi files are split into 1° by 1° grids. File names refer to the latitude and longitude of the lower left corner of the tile - e.g. N37W105 has its lower left corner at 37 degrees north latitude and 105 degrees west longitude. For example:  N37W105: `https://tile.mapzen.com/mapzen/terrain/v1/skadi/N37/N37W105.hgt.gz`.

#### Additional Amazon S3 Endpoints

If you’re building in Amazon AWS we recommend using machines in the `us-east` region (the same region as the S3 bucket) and use the following endpoints for increased performance:

* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif`
* `https://s3.amazonaws.com/elevation-tiles-prod/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`

NOTE: The S3 tiles are meant for efficient networking with EC2 resources only. The Amazon S3 endpoints are not cached using Cloudfront, but you could put your own Cloudfront or other CDN in front of them (or use Mapzen's Terrain Tiles service).

## Security

Mapzen Terrain Tiles works over HTTPS, in addition to HTTP. You are strongly encouraged to use HTTPS for all requests, especially for queries involving potentially sensitive information.
