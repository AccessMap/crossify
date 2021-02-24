import click
import geopandas as gpd
from os import path
import osmnx as ox
import numpy as np

from . import crossings, intersections, io, validators
from .opensidewalks import make_links


# Have to add extra layers
# FIXME: 'layer' is not correctly processed in osmnx. Other tags get turned
# into arrays if the ways get combined. Also, ways shouldn't be combined if
# they they are on different layers anyways, so may need to drop osmnx /
# simplify ourselves
USEFUL_TAGS_PATH = [
    "access",
    "area",
    "bridge",
    "est_width",
    "highway",
    "landuse",
    "lanes",
    "oneway",
    "maxspeed",
    "name",
    "ref",
    "service",
    "tunnel",
    "width",
    "layer",
]

ox.utils.config(
    cache_folder=path.join(path.dirname(__file__), "../cache"),
    useful_tags_path=USEFUL_TAGS_PATH,
    use_cache=True,
)

# Groups:
#   - Download all data from OSM bounding box, produce OSM file
#   - Download all data from OSM bounding box, produce GeoJSON file
#   - Provide own sidewalks data, produce OSM file
#   - Provide own sidewalks data, produce GeoJSON file

# So, the arguments are:
#   - Where is the info coming from? A file or a bounding box in OSM?
#   - What is the output format?

# crossify osm_bbox [bbox] output.geojson
# crossify from_file sidewalks.geojson output.geojson


@click.group()
def crossify():
    pass


@crossify.command()
@click.argument("sidewalks_in")
@click.argument("outfile")
def from_file(sidewalks_in, outfile):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.read_sidewalks(sidewalks_in)
    core(sidewalks, outfile)


@crossify.command()
@click.argument("west")
@click.argument("south")
@click.argument("east")
@click.argument("north")
@click.argument("outfile")
@click.option("--opensidewalks", is_flag=True)
def osm_bbox(west, south, east, north, outfile, opensidewalks):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.fetch_sidewalks(west, south, east, north)
    core(sidewalks, outfile, opensidewalks=opensidewalks)


def core(sidewalks, outfile, opensidewalks=False):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    click.echo("Fetching street network from OpenStreetMap...", nl=False)

    G_streets = io.fetch_street_graph(sidewalks)

    click.echo("Done")

    # Work in UTM
    sidewalks_u = ox.projection.project_gdf(sidewalks)

    # Extract street graph
    click.echo("Generating street graph...", nl=False)

    G_streets_u = ox.projection.project_graph(G_streets)
    # Fix the layer value
    for u, v, k, l in G_streets_u.edges(keys=True, data="layer", default=0):
        layer = validators.transform_layer(l)
        G_streets_u.edges[u, v, k]["layer"] = layer

    click.echo("Done")

    # Extract streets from streets graph
    click.echo("Extracting geospatial data from street graph...", nl=False)

    # Get the undirected street graph
    G_undirected_u = ox.save_load.get_undirected(G_streets_u)
    streets = ox.save_load.graph_to_gdfs(G_undirected_u, nodes=False, edges=True)
    streets.crs = sidewalks_u.crs

    click.echo("Done")

    #
    # Isolate intersections that need crossings (degree > 3), group with
    # their streets (all pointing out from the intersection)
    #
    click.echo("Isolating street intersections...", nl=False)

    ixns = intersections.group_intersections(G_streets_u)

    click.echo("Done")

    #
    # Draw crossings using the intersection + street + sidewalk info
    #
    click.echo("Drawing crossings...", nl=False)

    # Implied default value of 'layer' is 0, but it might be explicitly
    # described in some cases. Don't want to accidentally compare 'nan' to 0
    # and get 'False' when those are implicitly true in OSM
    validators.standardize_layer(sidewalks_u)

    st_crossings = crossings.make_crossings(ixns, sidewalks_u)
    if st_crossings is None:
        click.echo("Failed to make any crossings!")
        return

    if "layer" in sidewalks_u.columns:
        keep_cols = ["geometry", "layer"]
    else:
        keep_cols = ["geometry"]
    st_crossings = gpd.GeoDataFrame(st_crossings[keep_cols])
    st_crossings.crs = sidewalks_u.crs

    click.echo("Done")

    #
    # Schema correction stuff
    #

    st_crossings["highway"] = "footway"
    st_crossings["footway"] = "crossing"

    #
    # Write to file
    #

    click.echo("Writing to file...", nl=False)

    if opensidewalks:
        # If the OpenSidewalks schema is desired, transform the data to OSM
        # schema
        st_crossings, sw_links = make_links(st_crossings, offset=1)
        st_crossings["layer"] = st_crossings["layer"].replace(0, np.nan)
        sw_links["layer"] = sw_links["layer"].replace(0, np.nan)

        base, ext = path.splitext(outfile)
        sw_links_outfile = "{}_links{}".format(base, ext)
        io.write_sidewalk_links(sw_links, sw_links_outfile)

    io.write_crossings(st_crossings, outfile)

    click.echo("Done")
