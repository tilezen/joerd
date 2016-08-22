# Use raster elevation tiles

To use elevation tiles, you first need to obtain an API key from Mapzen. Sign in at https://mapzen.com/developers to create and manage your API keys.

Now, just append your API key into this URL pattern to get started, where `elevation-tiles-xxxxxxx` represents your key.

`https://tile.mapzen.com/{format}/v1/{z}/{x}/{y}.{ext}?api_key=elevation-tiles-xxxxxxx`

The [OpenStreetMap Wiki](http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) has more information on this url scheme.

## Available tile formats

Mapzen raster elevation tiles can be returned in the following formats.

#### Requesting tiles

The URL endpoints are cached on Mapzen's global CDN:

- **Terrarium**

  `https://tile.mapzen.com/terrarium/v1/{z}/{x}/{y}.png?api_key=elevation-tiles-xxxxxxx`

- **Normal**

  `
https://tile.mapzen.com/normal/v1/{z}/{x}/{y}.png?api_key=elevation-tiles-xxxxxxx`

- **GeoTIFF**

  `
https://tile.mapzen.com/geotiff/v1/{z}/{x}/{y}.tif?api_key=elevation-tiles-xxxxxxx`

  Note: GeoTIFF format tiles are 512x512 sized so request the parent tile’s coordinate. For instance, if you’re looking for a zoom 14 tile then request the parent tile at zoom 13.


- **Skadi**

  `
https://tile.mapzen.com/skadi/v1/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz?api_key=elevation-tiles-xxxxxxx`


Here’s a sample Terrarium in PNG format:

- `https://tile.mapzen.com/terrarium/v1/0/0/0.png?api_key=elevation-tiles-xxxxxxx`


#### Additional Amazon S3 Endpoints

If you’re building in Amazon AWS we recommend using machines in the `us-east` region (the same region as the S3 bucket) and use the following endpoints for increased performance:

* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif`
* `https://s3.amazonaws.com/elevation-tiles-prod/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`

NOTE: The S3 tiles are meant for efficent networking with EC2 resources only. The Amazon S3 endpoints are not cached using Cloudfront, but you could put your own Cloudfront or other CDN in fron tof them.

## Security

Mapzen Elevation Tiles works over HTTPS, in addition to HTTP. You are strongly encouraged to use HTTPS for all requests, especially for queries involving potentially sensitive information.