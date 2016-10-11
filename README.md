 Joerd, can be used to download, merge and generate tiles from digital elevation data. These tiles can then be used in a variety of ways; for map display in Walkabout, in [Valhalla's](https://github.com/valhalla) [Skadi](https://github.com/valhalla/skadi) for elevation influenced routing. In keeping with the Norse mythological theme used by Valhalla, the jotunn/goddess [Jörð](https://en.wikipedia.org/wiki/J%C3%B6r%C3%B0) was chosen as she is the personification of the Earth.

How do I pronounce it?
----------------------

Jörð is [pronounced](assets/joerd_pronunciation.mp3):

* j = y as in english 'yellow'
* ö = ö as in german 'Göttin'
* r = r as in spanish 'pero'
* ð = th as in english 'they'

Which is close to "y-earthe". Many thanks to [@baldur](https://github.com/baldur) for lending us his voice.

Building
--------

Build status: [![CircleCI](https://circleci.com/gh/tilezen/joerd.svg?style=svg)](https://circleci.com/gh/tilezen/joerd)

Joerd is a Python command line tool using `setuptools`. To install on a Debian or Ubuntu system, you need to install its dependencies:

```sh
sudo apt-get install python-gdal python-bs4 python-numpy gdal-bin python-setuptools python-shapely
```

(NOTE: not sure if this works: I installed GDAL-2.0.1 manually here, but I don't think it really needs it.)

You can then install it (recommended in a `virtualenv`) by running:

```sh
python setup.py install
```

Using
-----

Joerd installs as a command line library, and there are currently three commands:

* `server` starts up Joerd as a server listening for jobs on a queue. It is intended for use as part of a cluster to parallelise very large job runs.
* `enqueue-downloads` reads a config file and outputs a job to the queue for each source file needed by an output file in any configured region listed in the `regions` of the configuration file. This is intended for filling the queue for `server` to get work out of, but can also be used for local testing along with the `fake` queue type.
* `enqueue-renders` reads a config file and outputs a job to the queue for each output file in each region listed in the `regions` of the configuration file. This is intended for filling the queue for `server` to get work out of, but can also be used for local testing with the `fake` queue type.

There is also a `script/generate.py` program to generate a configuration with lots of little jobs all split up.

To run a command, type something like this:

```sh
joerd <command> --config config.example.yaml
```

Where `<command>` is one of the commands above (currently only `process`). The config has five sections:

* `regions` is a map of named sections, each with a `bbox` section having `top`, `left`, `bottom` and `right` coordinates. These describe the bounding box of the region. Data from the sources will be downloaded to cover that region, and outputs within it will be generated.
* `outputs` is a list of output plugins. Currently available:
  * `skadi` creates output in SRTMHGT format suitable for use in [Skadi](https://github.com/valhalla/skadi).
  * `terrarium` creates tiled output in GeoTIFF format.
* `sources` is a list of source plugins. Currently available:
  * `etopo1` downloads data from ETOPO1, a 1 arc-minute global bathymetry and topology dataset.
  * `gmted` downloads data from GMTED, a global topology dataset at 30 or 15 arc-seconds.
  * `srtm` downloads data from SRTM, an almost-global 3 arc-second topology dataset.
* `logging` has a single section, `config`, which gives the location of a Python logging config file.
* `cluster` contains the queue configuration.
  * `queue` is used for all job communication, and can be either `sqs` or `fake`:
    * `type` should be either `sqs` to use SQS for communicating jobs, or `fake` to run jobs immediately (i.e: not queue them at all).
	* `queue_name` (`sqs` only) the name of the SQS queue to use.
* `store` is the store used to put output tiles after they have been rendered. The store should indicate a `type` and some extra configuration as sub-keys:
  * `type` should be either `s3` to store files in Amazon S3, or `file` to store them on the local file system.
  * `base_dir` (`file` only) the filesystem path to use as a prefix for stored files.
  * `bucket_name` (`s3` only) the name of the bucket to store into.
  * `upload_config` (`s3` only) a dictionary of additional parameters to pass to the upload function.
* `source_store` is the store to download source files to when processing a download job, and retrieve them from when processing a render job. Note that _all_ the source files needed by the render jobs must be present in the source store before the render jobs are run. Configuration is the same as for `store`.

Caveats
-------

When using SRTM source HGT files, it's possible to run into [this bug](https://trac.osgeo.org/gdal/ticket/3305). The work-around given in the issue (export `GDAL_SKIP=JPEG`) appears to work.

License
-------

Joerd uses the [MIT License](COPYING).

Contributing
------------

We welcome contributions to Joerd. If you would like to report an issue, or even better fix an existing one, please use the [Joerd issue tracker](https://github.com/tilezen/joerd/issues) on GitHub.

Tests
-----

We highly encourage running and updating the tests to make sure no regressions have been made. This can be done by running:

```sh
python setup.py test
```
