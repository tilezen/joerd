# Get started with Mapzen Terrain Tiles

The Mapzen terrain tiles provide basemap elevation coverage of the world in a raster tile format. Tiles are available for zooms 0 through 15 and are available in several spatial data formats including PNG and GeoTIFF. The tiles also can be in a raw elevation and processed normal value format that's optimized for mobile and web display, and desktop analytical use. Data is available in both Web Mercator (EPSG:3857) projected and raw latlng. Learn more about the [various data formats](formats.md) offered.

## Get an API key

To start integrating Mapzen's hosted terrain tiles to your project you need a [developer API key](https://mapzen.com/documentation/overview/).

Once you have your Mapzen API key you'll need include it with Terrain Tile requests as a [URL query string](https://en.wikipedia.org/wiki/Query_string) like:

```
?api_key=your-mapzen-api-key
```

## Requesting tiles

The [OpenStreetMap Wiki](http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) describes the web mapping tile scheme used by the Mapzen terrain tile service.

Request a single tile with this URL pattern to get started:

```
https://tile.mapzen.com/mapzen/terrain/v1/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

Some formats support a `tilesize` option, see below for more information:

```
https://tile.mapzen.com/mapzen/terrain/v1/{tilesize}/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

Here's a sample tile in Normal format:

```
http://tile.mapzen.com/mapzen/terrain/v1/normal/11/330/790.png?api_key=your-mapzen-api-key
```

##### Terrarium

```
https://tile.mapzen.com/mapzen/terrain/v1/terrarium/{z}/{x}/{y}.png?api_key=your-mapzen-api-key
```

Supported optional tile size variants:

  `https://tile.mapzen.com/mapzen/terrain/v1/{256,512,260,516}/terrarium/{z}/{x}/{y}.png`

The 260 and 516 variants contain 2 pixels of buffering on each edge.

##### Normal

```
https://tile.mapzen.com/mapzen/terrain/v1/normal/{z}/{x}/{y}.png?api_key=your-mapzen-api-key
```

Supported optional tile size variants:

  `https://tile.mapzen.com/mapzen/terrain/v1/{256,512,260,516}/normal/{z}/{x}/{y}.png`

The 260 and 516 variants contain 2 pixels of buffering on each edge.

##### GeoTIFF

```
https://tile.mapzen.com/mapzen/terrain/v1/geotiff/{z}/{x}/{y}.tif?api_key=your-mapzen-api-key
```

Note: GeoTIFF format tiles are 512x512 sized so request the parent tile’s coordinate. For instance, if you’re looking for a zoom 14 tile then request the parent tile at zoom 13.

##### Skadi

```
https://tile.mapzen.com/mapzen/terrain/v1/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz?api_key=your-mapzen-api-key
```

Note: Skadi files are split into 1° by 1° grids. File names refer to the latitude and longitude of the lower left corner of the tile - e.g. N37W105 has its lower left corner at 37 degrees north latitude and 105 degrees west longitude. For example:  N37W105: `https://tile.mapzen.com/mapzen/terrain/v1/skadi/N37/N37W105.hgt.gz?api_key=your-mapzen-api-key`.

## Specify tile size

Both Terrarium and Normal formats support optional tile sizes of `256` and `512` for basic map display, and buffered sizes of `260` and `516` pixels useful for 3d and analytical applications. When not provided, the size defaults to `256`. Historically, the first web slippy maps were based on 256 pixel sized tiles.

```
https://tile.mapzen.com/mapzen/terrain/v1/{tilesize}/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

**Larger 512 pixel sized tiles offer several benefits:**

- **Less tiles, less network requests:** a single 512 request is equivalent to four 256 requests
- **Smaller overall file sizes:** A larger 512 pixel tile compresses to a smaller file size than when split into four 256 tiles
- **Offline:** Less 512 tiles are needed to cover the same geographic area, and take up less disk space

**Buffered 260 and 516 pixel sized tiles offer several benefits:**

- **Less network requests:** The 2 pixel edge buffers reduce network requests from 9 to 1, as sampling neighboring tiles is no longer necessary. And a single 516 request is equivalent to four 260 requests.
- **3D geometry construction**: The buffer provides enough height values in the overlap to calculate 3D elevation meshes without loading neighboring tiles.
- **Enables professional shading for 3D**: The 2nd pixel of buffer enables custom normals (slopes) to be calculated for the 1st pixel of the terrarium buffer without loading neighboring tiles.

### 256 tile size (default)

The maximum `{z}` value for 256 pixel tiles is zoom **15**. Requesting `{z}` coordinates past that will result in a 404 error.

**Default:**

Including tile size in the path is not required. When not specified the default size of `256` is returned, and Tangram's default `tile_size` of 256 is used.

```
https://tile.mapzen.com/mapzen/terrain/v1/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

**Example Tangram YAML:**

```
sources:
    mapzen:
        type: Raster
        url:  https://tile.mapzen.com/mapzen/terrain/v1/normal/{z}/{x}/{y}.png
        url_params:
            api_key: your-mapzen-api-key
        max_zoom: 15
```

**256 in path:**

```
https://tile.mapzen.com/mapzen/terrain/v1/256/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

### 512 tile size

The maximum `{z}` value for 512 pixel tiles is zoom **14**. Requesting `{z}` coordinates past that will result in a 404 error.

**512 in path:**

```
https://tile.mapzen.com/mapzen/terrain/v1/512/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

**Example Tangram YAML:**

```
sources:
    mapzen:
        type: MVT
        url:  https://tile.mapzen.com/mapzen/terrain/v1/512/normal/{z}/{x}/{y}.png
        url_params:
            api_key: your-mapzen-api-key
        tile_size: 512
        max_zoom: 14
```

### 260 tile size

The maximum `{z}` value for 260 pixel buffered tiles is zoom **15**. Requesting `{z}` coordinates past that will result in a 404 error. Supported by Terrarium and Normal formats.

**260 in path:**

```
https://tile.mapzen.com/mapzen/terrain/v1/260/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

### 516 tile size

The maximum `{z}` value for 516 pixel buffered tiles is zoom **14**. Requesting `{z}` coordinates past that will result in a 404 error. Supported by Terrarium and Normal formats.

**516 in path:**

```
https://tile.mapzen.com/mapzen/terrain/v1/516/{format}/{z}/{x}/{y}.{extension}?api_key=your-mapzen-api-key
```

#### Additional Amazon S3 Endpoints

If you’re building in Amazon AWS we recommend using machines in the `us-east` region (the same region as the S3 bucket) and use the following endpoints for increased performance:

* `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/normal/{z}/{x}/{y}.png`
* `https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif`
* `https://s3.amazonaws.com/elevation-tiles-prod/skadi/{N|S}{y}/{N|S}{y}{E|W}{x}.hgt.gz`

NOTE: The S3 tiles are meant for efficient networking with EC2 resources only. Terrarium and normal formats are only available as 256 tile size on the Amazon S3 endpoints. The Amazon S3 endpoints are not cached using Cloudfront, but you could put your own Cloudfront or other CDN in front of them (or use Mapzen's hosted Terrain Tiles service).

## Security

Mapzen Terrain Tiles works over HTTPS, in addition to HTTP. You are strongly encouraged to use HTTPS for all requests, especially for queries involving potentially sensitive information.
