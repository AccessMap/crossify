import os
import shutil
from tempfile import mkdtemp

import geopandas as gpd
import osmnx as ox
import overpass
from shapely.geometry import shape

from . import validators


def read_sidewalks(path):
    sidewalks = gpd.read_file(path)

    # Validate/convert input geometries, e.g. all LineStrings.
    sidewalks = validators.validate_sidewalks(sidewalks)

    # Use WGS84 to start
    sidewalks_wgs84 = sidewalks.to_crs({"init": "epsg:4326"})

    return sidewalks_wgs84


def fetch_sidewalks(west, south, east, north):
    api = overpass.API()
    footpaths_filter = "[highway=footway][footway=sidewalk]"
    response = api.Get(
        "way{}({},{},{},{})".format(footpaths_filter, south, west, north, east)
    )
    # Response is a GeoJSON FeatureCollection: convert to GeoDataFrame
    rows = []
    for feature in response["features"]:
        data = feature["properties"]
        data["geometry"] = shape(feature["geometry"])
        rows.append(data)

    gdf = gpd.GeoDataFrame(rows)
    gdf.crs = {"init": "epsg:4326"}

    return gdf


def fetch_street_graph(sidewalks):
    # Just in case, attempt to reproject
    sidewalks = sidewalks.to_crs({"init": "epsg:4326"})
    west, south, east, north = sidewalks.total_bounds
    G_streets = ox.graph.graph_from_bbox(north, south, east, west, network_type="drive")

    return G_streets


def write_crossings(crossings, path):
    # Just in case, attempt to reproject
    crossings = crossings.to_crs({"init": "epsg:4326"})

    # Create a temporary directory and attempt to write the file
    tempdir = mkdtemp()
    tempfile = os.path.join(tempdir, "crossings.geojson")

    # TODO: Check if extension is .osm and if so, apply proper schema and
    # osmify (user osmizer?)

    try:
        crossings.to_file(tempfile, driver="GeoJSON")
    except Exception as e:
        shutil.rmtree(tempdir)
        raise e

    # Writing was successful, so move the file to the correct path
    shutil.move(tempfile, path)


def write_sidewalk_links(links, path):
    # Just in case, attempt to reproject
    links = links.to_crs({"init": "epsg:4326"})

    # Create a temporary directory and attempt to write the file
    tempdir = mkdtemp()
    tempfile = os.path.join(tempdir, "links.geojson")

    # TODO: Check if extension is .osm and if so, apply proper schema and
    # osmify (user osmizer?)

    try:
        links.to_file(tempfile, driver="GeoJSON")
    except Exception as e:
        shutil.rmtree(tempdir)
        raise e

    # Writing was successful, so move the file to the correct path
    shutil.move(tempfile, path)
