import click
from os import path
import osmnx as ox

from . import crossings, intersections, io


# TODO: See if there's a more proper way to find the project root dir
# TODO: use a temporary dir?
ox.utils.config(cache_folder=path.join(path.dirname(__file__), '../cache'),
                use_cache=True)

# Groups:
#   - Download all data from OSM bounding box, produce OSM file
#   - Download all data from OSM bounding box, produce GeoJSON file
#   - Provide own sidewalks data, produce OSM file
#   - Provide own sidewalks data, produce GeoJSON file

# So, the arguments are:
#   - Where is the info coming from? A file or a bounding box in OSM?
#   - What is the output format?

# crossify from_bbox [bbox] output.extension
# crossify from_file sidewalks.geojson output.extension


@click.group()
def crossify():
    pass


@crossify.command()
@click.argument('sidewalks_in')
@click.argument('outfile')
def from_file(sidewalks_in, outfile):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.read_sidewalks(sidewalks_in)
    core(sidewalks, outfile)


@crossify.command()
@click.argument('west')
@click.argument('south')
@click.argument('east')
@click.argument('north')
@click.argument('outfile')
@click.option('--debug', is_flag=True)
def from_bbox(west, south, east, north, outfile, debug):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.fetch_sidewalks(west, south, east, north)
    core(sidewalks, outfile, debug)


def core(sidewalks, outfile, debug=False):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    click.echo('Fetching street network from OpenStreetMap...')
    G_streets = io.fetch_street_graph(sidewalks)

    # Work in UTM
    click.echo('Generating street graph...')
    G_streets_u = ox.projection.project_graph(G_streets)
    sidewalks_u = ox.projection.project_gdf(sidewalks)

    # Get the undirected street graph
    G_undirected_u = ox.save_load.get_undirected(G_streets_u)

    # Extract streets from streets graph
    click.echo('Extracting geospatial data from street graph...')
    streets = ox.save_load.graph_to_gdfs(G_undirected_u, nodes=False,
                                         edges=True)
    streets.crs = sidewalks_u.crs

    #
    # Isolate intersections that need crossings (degree > 3), group with
    # their streets (all pointing out from the intersection)
    #
    click.echo('Isolating street intersections...')
    ixns = intersections.group_intersections(G_streets_u)

    #
    # Draw crossings using the intersection + street + sidewalk info
    #
    click.echo('Drawing crossings...')
    st_crossings = crossings.make_crossings(ixns, sidewalks_u, debug=debug)
    if debug:
        st_crossings, street_segments = st_crossings

    #
    # Write to file
    #
    click.echo('Writing to file...')
    io.write_crossings(st_crossings, outfile)
    if debug:
        base, ext = path.splitext(outfile)
        debug_outfile = '{}_debug{}'.format(base, ext)
        io.write_debug(street_segments, debug_outfile)


if __name__ == '__main__':
    crossify()
