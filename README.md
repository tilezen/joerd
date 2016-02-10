     ██▒   █▓ ▄▄▄       ██▓     ██░ ██  ▄▄▄       ██▓     ██▓    ▄▄▄
    ▓██░   █▒▒████▄    ▓██▒    ▓██░ ██▒▒████▄    ▓██▒    ▓██▒   ▒████▄
     ▓██  █▒░▒██  ▀█▄  ▒██░    ▒██▀▀██░▒██  ▀█▄  ▒██░    ▒██░   ▒██  ▀█▄
      ▒██ █░░░██▄▄▄▄██ ▒██░    ░▓█ ░██ ░██▄▄▄▄██ ▒██░    ▒██░   ░██▄▄▄▄██
       ▒▀█░   ▓█   ▓██▒░██████▒░▓█▒░██▓ ▓█   ▓██▒░██████▒░██████▒▓█   ▓██▒
       ░ ▐░   ▒▒   ▓▒█░░ ▒░▓  ░ ▒ ░░▒░▒ ▒▒   ▓▒█░░ ▒░▓  ░░ ▒░▓  ░▒▒   ▓▒█░
       ░ ░░    ▒   ▒▒ ░░ ░ ▒  ░ ▒ ░▒░ ░  ▒   ▒▒ ░░ ░ ▒  ░░ ░ ▒  ░ ▒   ▒▒ ░
         ░░    ░   ▒     ░ ░    ░  ░░ ░  ░   ▒     ░ ░     ░ ░    ░   ▒
          ░        ░  ░    ░  ░ ░  ░  ░      ░  ░    ░  ░    ░  ░     ░  ░
         ░

Valhalla is an open source routing engine and accompanying libraries for use with Open Street Map data. This code, Joerd, can be used to download, merge and generate tiles from digital elevation data. These tiles can then be used in a variety of ways; for display, in [Skadi](https://github.com/valhalla/skadi) for routing, etc... In keeping with the Norse mythological theme, the jotunn/goddess [Jörð](https://en.wikipedia.org/wiki/J%C3%B6r%C3%B0) was chosen as she is the personification of the Earth.

How do I pronounce it?
----------------------

Jörð is [pronounced](assets/joerd_pronunciation.mp3):

* j = y as in english 'yellow'
* ö = ö as in german 'Göttin'
* r = r as in spanish 'pero'
* ð = th as in english 'they'

Which is close to "y-earthe". Many thanks to @baldur for lending us his voice.

Build Status
------------

[![Circle CI](https://circleci.com/gh/mapzen/joerd.svg?style=svg)](https://circleci.com/gh/mapzen/joerd)

Building
--------

Joerd is a Python command line tool using `setuptools`. To install on a Debian or Ubuntu system, you need to install its dependencies:

```sh
sudo apt-get install python-gdal python-bs4 python-numpy gdal-bin
```

(NOTE: not sure if this works: I installed GDAL-2.0.1 manually here, but I don't think it really needs it.)

You can then install it (recommended in a `virtualenv`) by running:

```sh
python setup.py install
```

Using
-----

Joerd installs as a command line library, and there is currently only one command:

* `process` reads the regions of interest from your config file, downloads all the sources to satisfy requests in that region, and for each tile intersecting the regions of interest in configured outputs, builds a [VRT](http://www.gdal.org/gdal_vrttut.html) "virtual dataset" of all relevant source files and generates the output image(s).

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
* `jobs` controls how Joerd runs jobs. The defaults are reasonable, so this whole section may be omitted. Current subsections are:
  * `num_threads` is how many threads to use when downloading files or generating output images. Defaults to the number of CPUs on the host computer.
  * `chunksize` is how many jobs to assign to a single thread at once. The default is a heuristic which tries to balance large chunk size for greater throughput and small chunk size for better load balance.

License
-------

Joerd, and all of the projects under the Valhalla organization use the [MIT License](COPYING).

Contributing
------------

We welcome contributions to Joerd. If you would like to report an issue, or even better fix an existing one, please use the [Joerd issue tracker](https://github.com/mapzen/joerd/issues) on GitHub.

Tests
-----

We highly encourage running and updating the tests to make sure no regressions have been made. This can be done by running:

```sh
python setup.py test
```
