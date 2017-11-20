'''Functions for validating and sprucing-up inputs.'''
import numpy as np


def validate_sidewalks(sidewalks):
    sidewalks_ls = sidewalks[sidewalks.type == 'LineString']
    n = sidewalks_ls.shape[0]
    if n:
        if n < sidewalks.shape[0]:
            m = sidewalks.shape[0] - n
            print('Warning: Removed {} non-LineString sidewalks'.format(m))
        return sidewalks_ls
    else:
        raise Exception('No LineStrings in sidewalks dataset: are they' +
                        ' MultiLineStrings?')


def validate_streets(streets):
    streets_ls = streets[streets.type == 'LineString']
    n = streets_ls.shape[0]
    if n:
        if n < streets.shape[0]:
            m = streets.shape[0] - n
            print('Warning: Removed {} non-LineString streets'.format(m))
        return streets_ls
    else:
        raise Exception('No LineStrings in streets dataset: are they' +
                        ' MultiLineStrings?')


def transform_layer(layer):
    # Convert nans to 0
    if layer is np.nan:
        return 0

    try:
        return int(layer)
    except ValueError:
        # Value can't be represented as integer - invalid schema, just
        # assume default layer
        return 0
    except TypeError:
        # Sometimes it's a list and that's annoying
        return int(layer[0])


def standardize_layer(gdf):
    if 'layer' in gdf.columns:
        gdf['layer'] = gdf['layer'].apply(transform_layer)
    else:
        gdf['layer'] = 0
