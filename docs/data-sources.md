# Data sources

Mapzen Terrain Tiles are powered by several major open data sets and we owe a tremendous debt of gratitude to the individuals and communities which produced them.

**Attribution is required** for some data providers. See the [Attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) document for more information.

## List of sources

The underlying data sources are a mix of:

- [3DEP](http://nationalmap.gov/elevation.html) (formerly NED) in the United States, 10 meters outside of Alaska, 3 meter in select land and territorial water areas
- [ArcticDEM](http://nga.maps.arcgis.com/apps/MapSeries/index.html?appid=cf2fba21df7540fb981f8836f2a97e25) strips of 5 meter mosaics across all of the land north of 60° latitude, including Alaska, Canada, Greenland, Iceland, Norway, and Russia
- [CDEM](http://geogratis.gc.ca/api/en/nrcan-rncan/ess-sst/c40acfba-c722-4be1-862e-146b80be738e.html) (Canadian Digital Elevation Model) in Canada, with variable spatial resolution (from 20-400 meters) depending on the latitude.
- [data.gov.uk](http://environment.data.gov.uk/ds/survey/index.jsp#/survey), 2 meters over most of the United Kingdom
- [data.gv.at](https://www.data.gv.at/katalog/dataset/b5de6975-417b-4320-afdb-eb2a9e2a1dbf), 10 meters over Austria
- [ETOPO1](https://www.ngdc.noaa.gov/mgg/global/global.html) to fill in ocean bathymetry at 1'
- [EUDEM](https://www.eea.europa.eu/data-and-maps/data/eu-dem#tab-original-data) in most of Europe at 30 meter resolution
- [GMTED](http://topotools.cr.usgs.gov/gmted_viewer/) globally, coarser resolutions at 7.5", 15", and 30" in land areas
- [Kartverket](http://data.kartverket.no/download/content/digital-terrengmodell-10-m-utm-33)'s Digital Terrain Model, 10 meters over Norway
- [LINZ](https://data.linz.govt.nz/layer/1768-nz-8m-digital-elevation-model-2012/), 8 meters over New Zealand
- [SRTM](https://lta.cr.usgs.gov/SRTM) globally except high latitudes, 30 meters in land areas

### Footprints database

These source images are composited to form tiles that make up the Mapzen Terrain Tiles service. To determine exactly which images contributed to Mapzen Terrain Tiles in a particular area, you can download the footprints database and use it with a GIS program like [QGIS](http://www.qgis.org/) to inspect which of these sources were used.

* [GeoJSON](https://example.com) (5.3MB, gzipped)
* [PostgreSQL Dump](https://example.com) (8.4MB, gzipped)

### Source headers

To further assist in determining which sources contributed to an individual tile, the Mapzen Terrain Tiles service will respond with an [HTTP header](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields#Response_fields) listing the sources that contributed to that tile. The value of the `X-Imagery-Sources` HTTP header is a comma-separated list, where each entry follows the pattern `source/filename.tif`.

For example, a tile might have the header `X-Imagery-Sources: srtm/N39W110.tif, srtm/N39W112.tif, gmted/30N120W_20101117_gmted_mea075.tif`, meaning that it was built from three source images. Two SRTM images and a GMTED image were composited together to generate the tile output. Using the footprint database dumps above you can gather more information about these source images, including the calculated resolution and footprint geometry. To find the entry in the database, look for an entry that has a matching `filename` attribute.


## What is the ground resolution?

Ground resolution per tile pixel varies per zoom level, the given pixel cell's latitude, and input data source.

This formula generates the following table:

`ground_resolution = (cos(latitude * pi/180) * 2 * pi * 6378137 meters) / (256 * 2^zoom_level pixels)`

Ground resolution per **zoom** in `meters` at a given _latitude_:

zoom   | _0°_       | _45°_      | _60°_
------ | ---------- | ---------- | ---------
**0**  | `156543.0` | `110692.6` | `78271.5`
**1**  | `78271.5`  | `55346.3`  | `39135.8`
**2**  | `39135.8`  | `27673.2`  | `19567.9`
**3**  | `19567.9`  | `13836.6`  | `9783.9`
**4**  | `9783.9`   | `6918.3`   | `4892.0`
**5**  | `4892.0`   | `3459.1`   | `2446.0`
**6**  | `2446.0`   | `1729.6`   | `1223.0`
**7**  | `1223.0`   | `864.8`    | `611.5`
**8**  | `611.5`    | `432.4`    | `305.7`
**9**  | `305.7`    | `216.2`    | `152.9`
**10** | `152.9`    | `108.1`    | `76.4`
**11** | `76.4`     | `54.0`     | `38.2`
**12** | `38.2`     | `27.0`     | `19.1`
**13** | `19.1`     | `13.5`     | `9.6`
**14** | `9.6`      | `6.8`      | `4.8`
**15** | `4.8`      | `3.4`      | `2.4`

**Note:** Esri has  [documentation](https://blogs.esri.com/esri/arcgis/2009/03/19/how-can-you-tell-what-map-scales-are-shown-for-online-maps/) about converting web map zoom integers to conventional map scales.

## What is sourced at what zooms?

Generally speaking, **GMTED** is used at low-zooms, and **ETOPO1** is used to show ocean bathymetry at all zooms (even bathymetry oversampled at zoom 15), and **[SRTM](http://www2.jpl.nasa.gov/srtm/)** is relied on in mid- and high-zooms on land. In the United States, data from **USGS** supplements the SRTM land data to provide greater detail at 10 meters and in some areas at up to 3 meters.

It should be noted that both `SRTM` and `GMTED` fill oceans and other bodies of water with a value of zero to indicate mean sea level; in these areas, `ETOPO1` provides bathymetry (as well as in regions which are not covered by `SRTM` and `GMTED`).

**Data sources per zoom:**

zoom   | ocean    | land
------ | -------- | -------
**0**  | `ETOPO1` | `GMTED`
**1**  | `ETOPO1` | `GMTED`
**2**  | `ETOPO1` | `GMTED`
**3**  | `ETOPO1` | `GMTED`
**4**  | `ETOPO1` | `GMTED`
**5**  | `ETOPO1` | `GMTED`
**6**  | `ETOPO1` | `GMTED`
**7**  | `ETOPO1` | `GMTED`
**8**  | `ETOPO1` | `GMTED`
**9**  | `ETOPO1` | `SRTM` with `GMTED` in high latitudes above 60°
**10** | `ETOPO1` | `SRTM` with `GMTED` in high latitudes above 60°
**11** | `ETOPO1` | `SRTM` with `GMTED` in high latitudes above 60°
**12** | `ETOPO1` | `SRTM` with `GMTED` and `NED/3DEP` in USA (10 meter)
**13** | `ETOPO1` | `SRTM` with `GMTED` and `NED/3DEP` in USA (10 meter)
**14** | `ETOPO1` | `SRTM` with `GMTED` and `NED/3DEP` in USA (mostly 10 meter, some 3 meter)
**15** | `ETOPO1` | `SRTM` with `GMTED` and `NED/3DEP` in USA (mostly 10 meter, some 3 meter)

## Sources native resolution

You might be wondering why we source from different data sets at different zooms. Besides bandwidth reasons, it's helpful to know the native resolution of each data set which is expressed as a nominal arc resolution which maps roughly to a web map zoom for "best displayed at".

In more practical terms, this results in some datasets being **"oversampled"** for a given zoom and map location.

* In the water, most bathymetry values at zoom 15 for a pixel that has a ground resolution of 5 meter will actually be showing an oversampled zoom 6 `ETOPO1` value (nominally 2.5 km).

* On the land, most elevation values at zoom 15 for a pixel that has a ground resolution of 5 meter will actually be showing an oversampled zoom 12 `SRTM` value (nominally 30 meters).

This formula generates the following table:

`ground_resolution = (cos(latitude * pi/180) * 2 * pi * 6378137 meters) / (256 * 2^zoom_level pixels) / 30.87 meters per arc second`

Arc resolution per **zoom** and data sources, per pixel:

zoom   | meters at equator     | arc seconds     | nominal arc degrees minutes seconds            | source      | nominal ground units
-----  | ---------- | -------- | ------------------- | --------    | --------------------
**0**  | _156543.0_ | `5071.0` | **1.5 arc degrees**  |             |
**1**  | _78271.5_  | `2535.5` | **40 arc minutes**   |             |
**2**  | _39135.8_  | `1267.8` | **20 arc minutes**   |             |
**3**  | _19567.9_  | `633.9`  | **10 arc minutes**   |             |
**4**  | _9783.9_   | `316.9`  | **5 arc minutes**    |             |
**5**  | _4892.0_   | `158.5`  | **2.5 arc minutes**  |             |
**6**  | _2446.0_   | `79.2`   | **1 arc minutes**    | `ETOPO1`    | 2.5 km
**7**  | _1223.0_   | `39.6`   | **30 arc seconds**   | `GMTED2010` | 1km  (not used)
**8**  | _611.5_    | `19.8`   | **15  arc seconds**  | `GMTED2010` | 500m (not used)
**9**  | _305.7_    | `9.9`    | **7.5  arc seconds** | `GMTED2010` | 250m
**10** | _152.9_    | `5.0`    | **5 arc seconds**    |             |
**11** | _76.4_     | `2.5`    | **3 arc seconds**    | `SRTM`      | 90m (not used)
**12** | _38.2_     | `1.2`    | **1 arc seconds**    | `SRTM`      | 30m
**13** | _19.1_     | `0.6`    | **2/3 arc seconds**  |             |
**14** | _9.6_      | `0.3`    | **1/3 arc seconds**  | `3DEP`      | 10m
**15** | _4.8_      | `0.2`    | **1/5 arc seconds**  |             |
**16** | _2.4_      | `0.1`    | **1/9 arc seconds**  | `3DEP`      | 3m

## Data updates

Terrain tiles were built during 2016Q2 and 2016Q3 based on available sources at that time. Regular updates are not planned.

Future updates will be on an as-needed basis for smaller regions to incorporate additional `3DEP` coverage in the United States and additional country specific data sources globally (such as `NRCAN` in Canada).

We are always looking for better datasets. If you find a data issue or can suggest an open terrain datasets, please let us know by filing an issue in [tilezen/joerd](https://github.com/tilezen/joerd/issues/new).

## Known issues

Many classical DEM and LIDAR related issues occur in terrain tiles. It is not uncommon to see large variations in elevation in areas with large buildings and other such structures. Resampling and merging artifacts are also observed along coastlines (where different datasets are seamed together).
