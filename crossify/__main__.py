import click
from os import path
import osmnx as ox

from . import crossings, intersections, io
from .opensidewalks import make_links


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
@click.option('--opensidewalks', is_flag=True)
def from_bbox(west, south, east, north, outfile, debug, opensidewalks):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.fetch_sidewalks(west, south, east, north)
    core(sidewalks, outfile, debug=debug, opensidewalks=opensidewalks)


def core(sidewalks, outfile, debug=False, opensidewalks=False):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    click.echo('Fetching street network from OpenStreetMap...', nl=False)

    G_streets = io.fetch_street_graph(sidewalks)

    click.echo('Done')

    # Work in UTM
    click.echo('Generating street graph...', nl=False)

    G_streets_u = ox.projection.project_graph(G_streets)
    sidewalks_u = ox.projection.project_gdf(sidewalks)

    # Get the undirected street graph
    G_undirected_u = ox.save_load.get_undirected(G_streets_u)

    click.echo('Done')

    # Extract streets from streets graph
    click.echo('Extracting geospatial data from street graph...', nl=False)

    streets = ox.save_load.graph_to_gdfs(G_undirected_u, nodes=False,
                                         edges=True)
    streets.crs = sidewalks_u.crs

    click.echo('Done')

    #
    # Isolate intersections that need crossings (degree > 3), group with
    # their streets (all pointing out from the intersection)
    #
    click.echo('Isolating street intersections...', nl=False)

    ixns = intersections.group_intersections(G_streets_u)

    click.echo('Done')

    #
    # Draw crossings using the intersection + street + sidewalk info
    #
    click.echo('Drawing crossings...', nl=False)

    st_crossings = crossings.make_crossings(ixns, sidewalks_u, debug=debug)
    if debug:
        st_crossings, street_segments = st_crossings

    click.echo('Done')

    #
    # If the OpenSidewalks schema is desired, transform the data to OSM schema
    #
    if opensidewalks:
        click.echo('Converting to OpenSidewalks schema...', nl=False)

        st_crossings, sw_links = make_links(st_crossings, offset=1)

        click.echo('Done')

    #
    # Write to file
    #
    click.echo('Writing to file...', nl=False)

    io.write_crossings(st_crossings, outfile)
    if opensidewalks:
        base, ext = path.splitext(outfile)
        sw_links_outfile = '{}_links{}'.format(base, ext)
        io.write_sidewalk_links(sw_links, sw_links_outfile)
    if debug:
        base, ext = path.splitext(outfile)
        debug_outfile = '{}_debug{}'.format(base, ext)
        io.write_debug(street_segments, debug_outfile)

    click.echo('Done')


if __name__ == '__main__':
    crossify()
