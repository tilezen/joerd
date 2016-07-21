# Adding a new data source

Example, using Great Lakes bathymetry.

To add a new data source, we have to write a "source" in Joerd. These are pieces of code which can be found in the `joerd/source/` subdirectory of the project. The sources are responsible for encapsulating how to download and unpack DEM data (digital elevation models, also known as DTM or digital terrain models) from sites on the internet, and calculate the intersection of these with bounding boxes of tiles.

We start the new `joerd/source/greatlakes.py` by enumerating the lakes and the bounding boxes of their source files and their datum offsets. Other data sets have a fixed relationship between the name of the file and the bounding box, for example, an SRTM file called `N50W001.SRTMGL1.hgt` covers a known bounding box and has a no datum offset to the projection's spheroid. However, that isn't the case with the Great Lakes data, and the bounding box can only be found from the source data. This is a bit of a design flaw, and we'll have to work around it by hard-coding the bounding boxes for now.

The datum offset can't even be found from the source data, and requires figuring out what the [mean low water datums](https://tidesandcurrents.noaa.gov/gldatums.html) are from somewhere else. This data will be used to reset the heights back to to the spheroid datum so that the height data matches the other sources.

Also hard-coded is the base URL for downloading the data, here as `BASE_URL`. This could be made configurable, if it were likely subject to change.

We add a `GreatLake` class, which represents a single downloadable item. This corresponds to the `SRTMTile` class in the `SRTM` source, but each Great Lake isn't a tile - just a named lake. This object is constructed by a factory called `GreatLakes`, which we'll get to later. The `GreatLake` class needs to be initialised, knowing its parent factory in order to access the variable holding the path to download files into and the name of the lake it represents.

`GreatLake` objects also need to be comparable, and hashable, on their identities. This excludes information such as the parent, or any download options, and in this case is based solely on the name of the lake. Thankfully, there are a limited set of Great Lakes and we don't have to worry about name collisions.

Other methods which need to be implemented include:

* `urls(self)` returns a list of URLs needed to download this lake. Other sources might need to download more than one file, but for the Great Lakes only one is needed. An example of something which downloads more than one file is SRTM, where each tile might have a corresponding shoreline mask.
* `verifier(self)` returns a function which can be used to check if a downloaded file is well-formed. The value here will depend on the type of file that's expected and, for Great Lakes data, we expect a `.tar.gz` format.
* `options(self)` returns the download options, a `dict` of parameters which can change how the download is performed. We require nothing special for the Great Lakes data, so just return the options what the factory passed to the constructor.
* `output_file(self)` returns the name of the output file, which can be chosen to make it easier for the code to keep track of the file. In the case of the Great Lakes data, there doesn't seem to be any advantage to call it anything other than the name of the lake.
* `unpack(self, store, tmp)` unpacks the downloaded file into the part or parts which are needed for the rest of Joerd to operate on it. In the case of Great Lakes data, we extract the GeoTIFF member of the `.tar.gz` archive, and use GDAL to reset the height to the global datum. This is also a bit of a design flaw - these adjustments would be better left until a later stage.
* `freeze_dry(self)` returns a `dict` containing all the data to identify this source file. When the list of rendering jobs is created, this is used to group together jobs which overlap the same source items to avoid re-downloading large source data items. This is kind of used as a poor substitute for designing the object correctly - the object itself really should be the "freeze dried" part, in which case regular serialization would have worked and `freeze_dry` and its partner `rehydrate` would not be necessary.

We also need to provide a factory object, `GreatLakes`, which can enumerate all the source data items. For other sources, this can be a large number of tiles, but for this source it's just the list of Great Lakes.

Methods which need implementing:

* `get_index(self)` would create an index, but that's unnecessary for a non-tiled source such as `GreatLakes`. Instead, we use this as a time to create the directories we need to download files into.
* `existing_files(self)` yields the name of each file from the local store which has already been downloaded.
* `rehydrate(self, data)` returns a `GreatLake` object constructed from the information in the data `dict`, which itself is the result of calling `freeze_dry` on a `GreatLake` object. A poor substitute for proper serialization.
* `downloads_for(self, tile)` returns a `set` of `GreatLake` objects which have bounding boxes intersecting the given `tile`. It also checks that the resolution of the data is appropriate, and that we aren't down-sampling too much.
* `vrts_for(self, tile)` returns a list of sets of source items (`GreatLake`s), where each entry in the list will be a separate VRT. This is to work around issues where GDAL will choose only a single value from the VRT at any given location, meaning a raster in a VRT with NODATA at a point might obscure another raster in the same VRT with data at that point. This is only a problem with datasets with overlapping sections which contain a lot of NODATA - mainly NED.
* `srs(self)` returns a Spatial Reference object for this dataset.
* `filter_type(self, src_res, dst_res)` returns the GDAL filter type enum to use for up- or down-scaling this raster.

Finally, we need to add a free function, `create(options)` which returns a factory `GreatLakes` based on the options given.

To enable this data source in a run of Joerd, it needs to be included in the config file. Because the resolution of the Great Lakes data is 3 arcseconds, which is better than GMTED but not as good as NED or SRTM, the best place is between SRTM and GMTED.
