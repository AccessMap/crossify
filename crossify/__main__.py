import click
from os import path
import osmnx as ox

from . import crossings, intersections, io


# TODO: See if there's a more proper way to find the project root dir
ox.utils.config(cache_folder=path.join(path.dirname(__file__), '../cache'),
                use_cache=True)


@click.command()
@click.argument('sidewalks_in')
@click.argument('outfile')
def crossify(sidewalks_in, outfile):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.read_sidewalks(sidewalks_in)
    G_streets = io.fetch_street_graph(sidewalks)

    # Work in UTM
    G_streets_u = ox.projection.project_graph(G_streets)
    sidewalks_u = ox.projection.project_gdf(sidewalks)

    # Get the undirected street graph
    G_undirected_u = ox.save_load.get_undirected(G_streets_u)

    # Extract streets from streets graph
    streets = ox.save_load.graph_to_gdfs(G_undirected_u, nodes=False,
                                         edges=True)
    streets.crs = sidewalks_u.crs

    #
    # Isolate intersections that need crossings (degree > 3), group with
    # their streets (all pointing out from the intersection)
    #
    ixns = intersections.group_intersections(G_streets_u)

    #
    # Draw crossings using the intersection + street + sidewalk info
    #
    st_crossings = crossings.make_crossings(ixns, sidewalks_u)

    #
    # Write to file
    #
    io.write_crossings(st_crossings, outfile)


if __name__ == '__main__':
    crossify()
