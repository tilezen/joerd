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
