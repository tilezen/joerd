# Get started with Mapzen Terrain Tiles

The Mapzen terrain tiles provide basemap elevation coverage of the world in a raster tile format. Tiles are available for zooms 0 through 15 and are available in several spatial data formats including PNG and GeoTIFF. The tiles also can be in a raw elevation and processed normal value format that's optimized for mobile and web display, and desktop analytical use. Data is available in both Web Mercator (EPSG:3857) projected and raw latlng. Learn more about the [various data formats](formats.md) offered.

## Get an API key

To start integrating Mapzen's hosted terrain tiles to your project you need a [developer API key](https://mapzen.com/documentation/overview/).

Once you have your Mapzen API key you'll need include it with Terrain Tile requests as a [URL query string](https://en.wikipedia.org/wiki/Query_string) like:

```
?api_key=your_mapzen_api_key
```

## Requesting tiles

Request a single tile with this URL pattern to get started:
  		  
```
https://tile.mapzen.com/mapzen/terrain/v1/{format}/{z}/{x}/{y}.{extension}?api_key={your_mapzen_api_key}
```
  		  
The [OpenStreetMap Wiki](http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) has more information on this url scheme.
  		  
Here’s a sample tile in Normal format:
  		  
```
http://tile.mapzen.com/mapzen/terrain/v1/normal/11/330/790.png?api_key=your_mapzen_api_key
```

##### Terrarium

```
https://tile.mapzen.com/mapzen/terrain/v1/terrarium/{z}/{x}/{y}.png?api_key={your_mapzen_api_key}
```

##### Normal

```
https://tile.mapzen.com/mapzen/terrain/v1/normal/{z}/{x}/{y}.png?api_key={your_mapzen_api_key}
```

##### GeoTIFF

```
https://tile.mapzen.com/mapzen/terrain/v1/geotiff/{z}/{x}/{y}.tif?api_key={your_mapzen_api_key}
```

Note: GeoTIFF format tiles are 512x512 sized so request the parent tile’s coordinate. For instance, if you’re looking for a zoom 14 tile then request the parent tile at zoom 13.

##### Skadi

```
https://tile.mapzen.com/mapzen/terrain/v1/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz?api_key={your_mapzen_api_key}
```

Note: Skadi files are split into 1° by 1° grids. File names refer to the latitude and longitude of the lower left corner of the tile - e.g. N37W105 has its lower left corner at 37 degrees north latitude and 105 degrees west longitude. For example:  N37W105: `https://tile.mapzen.com/mapzen/terrain/v1/skadi/N37/N37W105.hgt.gz?api_key={your_mapzen_api_key}`.

#### Additional Amazon S3 Endpoints

If you’re building in Amazon AWS we recommend using machines in the `us-east` region (the same region as the S3 bucket) and use the following endpoints for increased performance:

* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif`
* `https://s3.amazonaws.com/elevation-tiles-prod/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`

NOTE: The S3 tiles are meant for efficient networking with EC2 resources only. The Amazon S3 endpoints are not cached using Cloudfront, but you could put your own Cloudfront or other CDN in front of them (or use Mapzen's hosted Terrain Tiles service).

## Security

Mapzen Terrain Tiles works over HTTPS, in addition to HTTP. You are strongly encouraged to use HTTPS for all requests, especially for queries involving potentially sensitive information.
