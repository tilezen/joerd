# Data Sources

Mapzen Terrain Tiles are powered by several major open data sets and we owe a tremendous debt of gratitude to the individuals and communities which produced them.

**Attribution is required** for some of our data providers. See the [Attribution](attribution.md) document for more information.

## List of sources

The underlying data sources are a mix of:

- [3DEP](http://nationalmap.gov/elevation.html) (formerly NED) in the United States, 10 meters outside of Alaska, 3 meter in select land and territorial water areas
- [SRTM](https://lta.cr.usgs.gov/SRTM) globally except high latitudes, 30 meters in land areas
- [GMTED](http://topotools.cr.usgs.gov/gmted_viewer/) globally, coarser resolutions at 7.5", 15", and 30" in land areas
- [ETOPO1](https://www.ngdc.noaa.gov/mgg/global/global.html) to fill in ocean bathymetry at 1'


## What is the ground resolution?

Ground resolution per tile pixel varies per zoom level, the given pixel cell's latitude, and input data source.

This formula generates the following table:

`ground_resultion = (cos(latitude * pi/180) * 2 * pi * 6378137 meters) / (256 * 2^zoom_level pixels)`

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

It should be noted that both `SRTM` and `GMTED` fill oceans and other bodies of water with a value of zero to indicate mean sea level; in these areas, `ETOPO1` provides bathymetry (as well as in regions which are not coverged by `SRTM` and `GMTED`).

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

In more practicle terms, this results in some datasets being **"oversampled"** for a given zoom and map location.

* In the water, most bathymetry values at zoom 15 for a pixel that has a ground resolution of 5 meter will actually be showing an oversampled zoom 6 `ETOPO1` value (nominally 2.5 km).

* On the land, most elevation values at zoom 15 for a pixel that has a ground resolution of 5 meter will actually be showing an oversampled zoom 12 `SRTM` value (nominally 30 meters).

This formula generates the following table:

`ground_resultion = (cos(latitude * pi/180) * 2 * pi * 6378137 meters) / (256 * 2^zoom_level pixels) / 30.87 meters per arc second`

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

## Known issues

Many other classical DEM-related issues occur in these datasets. It is not uncommon to see large variations in elevation in areas with large buildings and other such structures. We are considering how to best integrate additional `NED/3DEP` and `NRCAN` sources, and are always looking for better datasets. If you find any data issues or can suggest any supplemental open datasets, please let us know by filing an issue in [tilezen/joerd](https://github.com/tilezen/joerd/issues/new).
