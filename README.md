# Crossify

`crossifyify` is a Python library and command line application for drawing
street crossing lines from street centerline and sidewalk centerline data.

## Introduction

Pedestrian transportation network data are often missing. `crossify` works in
concert with `sidewalkify` to help populate a minimal pedestrian network from
labeled street data, by drawing (first order approximations of) street
crossings given street and sidewalk data. `crossify` does not require the use
of `sidewalkify`.

## Installation

`pip install crossify`

`crossify` requires the `click` and `geopandas` libraries.
`geopandas` requires GDAL to read and write files, so you also need to install
GDAL tools for your system.

Python 2: though this package is currently marked as Python 3-only, it should
work on Python 2 as well. However, we do not currently support issues related
to Python 2.

## Usage

Once installed, `crossify` is available both as a command line application
and a Python library.

#### CLI

Example:

    crossify <streets.shp> <sidewalks.shp> <output.shp>

##### Arguments

The input file can be any file type readable by `geopandas.read_file`, which
should be anything readable by `fiona`, i.e. GDAL.

For example, you could also use a GeoJSON input file:

    crossify <streets.geojson> <sidewalks.geojson> <output.geojson>

#### Python Library

`crossify` can also be used as a Python library so that you can build your
own scripts or write libraries on top of `crossify`. We recommend that you
read the Architecture section before using the `crossify` library API.

# License

Dual-licensed MIT and Apache 2.0. You can treat this project as being licensed
under one or the other, depending on your preference.
