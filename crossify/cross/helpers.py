# CROSSING HELPERS
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import geometry

ORTHAGONAL_MIN_1 = np.pi * 1 / 4
ORTHAGONAL_MAX_1 = np.pi * 3 / 4
ORTHAGONAL_MIN_2 = np.pi * 5 / 4
ORTHAGONAL_MAX_2 = np.pi * 7 / 4

# compares orthagonality betweent two slopes in radians
def is_orthagonal(slope1, slope2):
    # (1/4 pi to 3/4 pi) and (5/4 pi to 7/4 pi) difference is orthagonal

    diff = abs(slope1 - slope2)

    if (ORTHAGONAL_MIN_1 < diff < ORTHAGONAL_MAX_1) or (ORTHAGONAL_MIN_2 < diff < ORTHAGONAL_MAX_2):
        return True
    else:
        return False

def azimuth(p1, p2):
    '''Azimuth function - calculates angle between two points in radians
    where 0 = north, in clockwise direction.'''
    radians = np.arctan2(p2[0] - p1[0], p2[1] - p1[1])
    if radians < 0:
        radians += 2 * np.pi
    return radians

# returns coners in sidewalk dataset
def get_corners(sidewalks):
    starts = sidewalks.geometry.apply(lambda x: geometry.Point(x.coords[0]))
    # ends = sidewalks.geometry.apply(lambda x: x.interpolate(x.length - link_offset_from_corner))
    ends = sidewalks.geometry.apply(lambda x: geometry.Point(x.coords[-1]))
    n = sidewalks.shape[0]
    ends = gpd.GeoDataFrame({
        'sw_index': 2 * list(sidewalks.index),
        # 'streets_pkey': 2 * list(sidewalks['streets_pkey']),
        'endtype': n * ['start'] + n * ['end'],
        # 'layer': 2 * list(sidewalks['layer']),
        'geometry': pd.concat([starts, ends])
    })

    ends.reset_index(drop=True, inplace=True)
    # Initialize the spatial index(s) (much faster distance queries)
    ends.sindex

    ends['wkt'] = ends.apply(lambda r: r.geometry.wkt, axis=1)

    grouped = ends.groupby('wkt')

    def extract(group):
        geom = group.iloc[0]['geometry']
        sw1_index = group.iloc[0]['sw_index']
        sw1type = group.iloc[0]['endtype']
        if group.shape[0] > 1:
            sw2_index = group.iloc[1]['sw_index']
            sw2type = group.iloc[1]['endtype']
        else:
            sw2_index = pd.np.nan
            sw2type = pd.np.nan
        # FIXME: there is probably a faster way to do this
        return gpd.GeoDataFrame({
            'geometry': [geom],
            'sw1_index': [sw1_index],
            'sw1type': [sw1type],
            'sw2_index': [sw2_index],
            'sw2type': [sw2type]
        })

    corners = grouped.apply(extract)
    corners.reset_index(drop=True, inplace=True)
    corners.sindex
    return corners
