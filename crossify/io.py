import os
import shutil
from tempfile import mkdtemp

import geopandas as gpd
import osmnx as ox

from . import validators


def read_sidewalks(path):
    sidewalks = gpd.read_file(path)

    # Validate/convert input geometries, e.g. all LineStrings.
    sidewalks = validators.validate_sidewalks(sidewalks)

    # Use WGS84 to start
    sidewalks_wgs84 = sidewalks.to_crs({'init': 'epsg:4326'})

    return sidewalks_wgs84


def fetch_street_graph(sidewalks):
    # Just in case, attempt to reproject
    sidewalks = sidewalks.to_crs({'init': 'epsg:4326'})
    west, south, east, north = sidewalks.total_bounds
    G_streets = ox.graph_from_bbox(north, south, east, west,
                                   network_type='drive')

    return G_streets


def write_crossings(crossings, path):
    # Just in case, attempt to reproject
    crossings = crossings.to_crs({'init': 'epsg:4326'})

    # Create a temporary directory and attempt to write the file
    tempdir = mkdtemp()
    tempfile = os.path.join(tempdir, 'crossings.geojson')

    try:
        crossings.to_file(tempfile, driver='GeoJSON')
    except Exception as e:
        shutil.rmtree(tempdir)
        raise e

    # Writing was successful, so move the file to the correct path
    os.rename(tempfile, path)
