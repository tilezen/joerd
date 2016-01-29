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

Build Status
------------

[![Circle CI](https://circleci.com/gh/valhalla/joerd.svg?style=svg)](https://circleci.com/gh/valhalla/joerd)

Building
--------

Joerd is a Python command line tool using `setuptools`. To install on a Debian or Ubuntu system, you need to install its dependencies:

```sh
sudo apt-get install python-gdal
```

(NOTE: not sure if this works: I installed GDAL-2.0.1 manually here, but I don't think it really needs it.)

You can then install it (recommended in a `virtualenv`) by running:

```sh
python setup.py install
```

Using
-----

Joerd installs as a command line library, and there are currently three commands:

* `download` reads the regions of interest from your config file and downloads all the sources to satisfy requests in that region. This is a prerequisite for the other steps.
* `buildvrt` builds a [VRT](http://www.gdal.org/gdal_vrttut.html) "virtual dataset" of all the downloaded files. This requires that you have already run `download`, and is a prerequisite of the `generate` step.
* `generate` generates all the configured outputs matching your regions of interest.

To run each command, type something like this:

```sh
joerd <command> --config config.example.yaml
```

Where `<command>` is one of the commands above. The config has four sections:

* `regions` is a map of named sections, each with a `bbox` section having `top`, `left`, `bottom` and `right` coordinates. These describe the bounding box of the region. Data from the sources will be downloaded to cover that region, and outputs within it will be generated.
* `outputs` is a list of output plugins. Currently available:
  * `skadi` creates output in SRTMHGT format suitable for use in [Skadi](https://github.com/valhalla/skadi).
  * `terrarium` creates tiled output in GeoTIFF format.
* `sources` is a list of source plugins. Currently available:
  * `etopo1` downloads data from ETOPO1, a 1 arc-minute global bathymetry and topology dataset.
  * `gmted` downloads data from GMTED, a global topology dataset at 30 or 15 arc-seconds.
  * `srtm` downloads data from SRTM, an almost-global 3 arc-second topology dataset.
* `logging` has a single section, `config`, which gives the location of a Python logging config file.

License
-------

Joerd, and all of the projects under the Valhalla organization use the [MIT License](COPYING).

Contributing
------------

We welcome contributions to Joerd. If you would like to report an issue, or even better fix an existing one, please use the [Joerd issue tracker](https://github.com/valhalla/joerd/issues) on GitHub.

Tests
-----

We highly encourage running and updating the tests to make sure no regressions have been made. This can be done by running:

```sh
python setup.py test
```
