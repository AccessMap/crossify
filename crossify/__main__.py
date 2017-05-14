import click
import geopandas as gpd

from . import populate, constrain, schema


@click.command()
@click.argument('sidewalks_in')
@click.argument('streets_in')
@click.argument('outfile')
def crossify(sidewalks_in, streets_in, outfile):
    # FIXME: these should be turned into configuration options
    intersections_only = True
    osm_schema = True

    sidewalks = gpd.read_file(sidewalks_in)
    streets = gpd.read_file(streets_in)

    # Ensure we're working in the same CRS as the sidewalks dataset
    crs = sidewalks.crs
    streets = streets.to_crs(crs)

    # FIXME: this is where we'd create the crossings
    dense_crossings = populate.populate(sidewalks, streets)

    if intersections_only:
        crossings = constrain.constrain(dense_crossings)
    else:
        crossings = dense_crossings

    if osm_schema:
        crossings = schema.apply_schema(crossings)

    crossings.to_file(outfile)

if __name__ == '__main__':
    crossify()
