# Get started with Mapzen Terrain Tiles

The [Mapzen terrain tiles](https://mapzen.com/projects/joerd) provide basemap elevation coverage of the world in a raster tile format. Tiles are available for zooms 0 through 15 and are available in several spatial data formats including PNG and GeoTIFF. The tiles also can be in a raw elevation and processed normal value format that's optimized for mobile and web display, and desktop analytical use. Data is available in both web Mercator projected and raw latlng. If you are familiar with digital elevation models (DEMs) or digital terrain models (DTMs), this service is for you.

## Get an API key

To use the Mapzen Terrain Tiles service, you must first get a developer API key. Sign in at https://mapzen.com/developers to create and manage your API keys.

1. Go to https://mapzen.com/developers.
2. Sign in with your GitHub account. If you have not done this before, you need to agree to the terms first.
3. Create a new key for Mapzen Search, and optionally, give it a name so you can remember the purpose of the project.
4. Copy the key into the terrain URL where `terrain-tiles-xxxxxxx` represents your key.

## Available tile formats

Mapzen raster terrain tiles can be returned in the following formats:

#### Requesting tiles

You can request tiles using Mapzen's global CDN:

##### Terrarium PNG

  `https://tile.mapzen.com/mapzen/terrain/v1/terrarium/{z}/{x}/{y}.png?api_key=terrain-tiles-xxxxxxx`

##### Terrarium GeoTIFF

  `https://tile.mapzen.com/mapzen/terrain/v1/terrarium/{z}/{x}/{y}.tif?api_key=terrain-tiles-xxxxxxx`

  Note: GeoTIFF format tiles are 512x512 sized so request the parent tile’s coordinate. For instance, if you’re looking for a zoom 14 tile then request the parent tile at zoom 13.

##### Normal

  `https://tile.mapzen.com/mapzen/terrain/v1/normal/{z}/{x}/{y}.png?api_key=terrain-tiles-xxxxxxx`

##### Skadi

  `https://tile.mapzen.com/mapzen/terrain/v1/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz?api_key=terrain-tiles-xxxxxxx`

#### Additional Amazon S3 Endpoints

If you’re building in Amazon AWS we recommend using machines in the `us-east` region (the same region as the S3 bucket) and use the following endpoints for increased performance:

* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.tif`
* `https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`

NOTE: The S3 tiles are meant for efficent networking with EC2 resources only. The Amazon S3 endpoints are not cached using Cloudfront, but you could put your own Cloudfront or other CDN in front of them.

## Security

Mapzen Terrain Tiles works over HTTPS, in addition to HTTP. You are strongly encouraged to use HTTPS for all requests, especially for queries involving potentially sensitive information.
