# Crossify

`crossify` is a Python library and command line application for drawing
street crossing lines from street centerline and sidewalk centerline data.

`crossify` has two usage modes:

- It can automatically fetch sidewalk data from OpenStreetMap
- It can read sidewalk data from a GIS file (e.g. GeoJSON or shapefile)

In both modes, it fetches street data from OpenStreetMap and uses the sidewalk
and street data to construct likely crossing locations.

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

### Sidewalks should be fetched from OpenStreetMap

To fetch sidewalk data from OpenStreetMap, use the `osm_bbox` command:

    crossify osm_bbox -- <west> <south> <east> <north> <output file>

The values of west, south, east, and north define a rectangular bounding box
for your query, and should be in terms of latitude (south, north) and longitude
(west, east). The use of a double dash is necessary for the use of negative
coordinates not getting parsed as command line options (see the example below).

Example:

    crossify osm_bbox -- -122.31846 47.65458 -122.31004 47.65783
    test/output/crossings.geojson

### A sidewalks file is provided

If you want to provide your own sidewalks layer, use the `from_file` command:

    crossify from_file <sidewalks file> <output file>

Example:

    crossify from_file test/input/sidewalks_udistrict.geojson
    test/output/crossings.geojson


#### Python Library

`crossify` can also be used as a Python library so that you can build your
own scripts or write libraries on top of `crossify`. We recommend that you
read the Architecture section before using the `crossify` library API.

# License

Dual-licensed MIT and Apache 2.0. You can treat this project as being licensed
under one or the other, depending on your preference.
