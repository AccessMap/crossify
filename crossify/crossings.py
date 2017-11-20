import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point, Polygon

from . import validators


def make_crossings(intersections_dict, sidewalks):
    crs = sidewalks.crs

    validators.standardize_layer(sidewalks)

    ixn_dat = []
    st_crossings = []

    # TODO: vectorize these operations for performance improvement?
    for i, (ixn, data) in enumerate(intersections_dict.items()):
        ixn_dat.append({
            'geometry': data['geometry'],
            'ixn': i
        })
        for street in data['streets']:
            # Protect against invalid inputs
            street['layer'] = validators.transform_layer(street['layer'])
            new_crossing = make_crossing(street, sidewalks, data['streets'])
            if new_crossing is not None:
                st_crossings.append(new_crossing)

    if not st_crossings:
        return None

    st_crossings = gpd.GeoDataFrame(st_crossings)
    st_crossings = st_crossings[st_crossings.type == 'LineString']
    st_crossings = st_crossings[st_crossings.is_valid]

    # Remove duplicates
    def comp(geom):
        p1 = np.round(geom.coords[0], 2)
        p2 = np.round(geom.coords[-1], 2)
        return str([p1, p2])

    comparison = st_crossings.geometry.apply(comp)
    comparison.name = 'comp'
    unique = st_crossings.groupby(comparison).first()
    st_crossings = gpd.GeoDataFrame(unique.reset_index())
    st_crossings.crs = crs

    return st_crossings


def make_crossing(street, sidewalks, streets_list):
    '''Attempts to create a street crossing line given a street segment and
    a GeoDataFrame sidewalks dataset. The street and sidewalks should have
    these properties:

    (1) The street should start at the street intersection and extend away
    from it.
    (2) The sidewalks should all be LineString geometries.

    If a crossing cannot be created that meets certain internal parameters,
    None is returned.

    :param street: The street geometry.
    :type street: shapely.geometry.LineString
    :param sidewalks: The sidewalks dataset.
    :type sidewalks: geopandas.GeoDataFrame
    :returns: If a crossing can be made, a shapely Linestring. Otherwise, None.
    :rtype: shapely.geometry.LineString or None

    '''
    # 'Walk' along the street in 1-meter increments, finding the closest
    # sidewalk + the distance along each end. Reject those with inappropriate
    # angles and differences in length.
    # TODO: this is a good place for optimizations, it's a search problem.
    # Can probably do something like binary search.

    # Clip street in half: don't want to cross too far in.
    # TODO: this should be done in a more sophisticated way. e.g. dead ends
    # shouldn't require this and we should use a max distance value as well
    # street = street.interpolate(0.5, normalized=True)

    # New idea: use street buffers of MAX_CROSSING_DIST + small delta, use
    # this to limit the sidewalks to be considered at each point. Fewer
    # distance and side-of-line queries!

    START_DIST = 4
    INCREMENT = 2
    MAX_DIST_ALONG = 25
    MAX_CROSSING_DIST = 30
    OFFSET = MAX_CROSSING_DIST / 2

    st_distance = min(street['geometry'].length / 2, MAX_DIST_ALONG)
    start_dist = min(START_DIST, st_distance / 2)
    layer = street['layer']

    # Create buffer for the street search area, one for each side, then find
    # the sidewalks intersecting that buffer - use as candidates for
    # right/left
    sw_left = get_side_sidewalks(OFFSET, 'left', street, sidewalks)
    sw_right = get_side_sidewalks(OFFSET, 'right', street, sidewalks)

    if sw_left.empty or sw_right.empty:
        # One of the sides has no sidewalks to connect to! Abort!
        return None

    # Restrict to sidewalks on the same 'layer' as the input
    sw_left = sw_left[sw_left['layer'] == layer]
    sw_right = sw_right[sw_right['layer'] == layer]

    if sw_left.empty or sw_right.empty:
        # One of the sides has no sidewalks to connect to! Abort!
        return None

    candidates = []
    for dist in np.arange(start_dist, st_distance, INCREMENT):
        crossing = crossing_from_dist(street['geometry'], dist, sw_left,
                                      sw_right)

        #
        # Filters
        #
        if not crossing['geometry'].intersects(street['geometry']):
            continue

        other_streets = []
        for st in streets_list:
            if st == street:
                continue
            if st['layer'] != layer:
                continue
            other_streets.append(st['geometry'])

        if other_streets:
            if crosses_other_streets(crossing['geometry'], other_streets):
                continue

        # The sides have passed the filter! Add their data to the list
        ixn = street['geometry'].intersection(crossing['geometry'])
        if ixn.type != 'Point':
            continue

        crossing_distance = street['geometry'].project(ixn)
        crossing['search_distance'] = dist
        crossing['crossing_distance'] = crossing_distance
        crossing['layer'] = layer

        candidates.append(crossing)

    if not candidates:
        return None

    # Return the shortest crossing.
    # TODO: Should also bias towards *earlier* appearances, i.e. towards
    # corner.
    # lengths = np.array([line['crossing'].length for line in lines])
    # # Inverse distance function (distance from intersection)
    # distance_metric = 1 / np.array([line['distance'] for line in lines])

    # lengths * distance_metric
    def cost(candidate):
        terms = []
        terms.append(candidate['geometry'].length)
        terms.append(2e-1 * candidate['crossing_distance'])
        return sum(terms)

    best = sorted(candidates, key=cost)[0]

    return best


def get_side_sidewalks(offset, side, street, sidewalks):
    # TODO: do this once for the whole street
    offset = street['geometry'].parallel_offset(offset, side, 0, 1, 1)
    if offset.type == 'MultiLineString':
        # Convert to LineString
        coords = []
        for geom in offset.geoms:
            coords += list(geom.coords)
        offset = LineString(coords)
    if side == 'left':
        offset.coords = offset.coords[::-1]
    st_buffer = Polygon(list(street['geometry'].coords) +
                        list(offset.coords) +
                        [street['geometry'].coords[0]])
    query = sidewalks.sindex.intersection(st_buffer.bounds, objects=True)
    query_sidewalks = sidewalks.loc[[q.object for q in query]]
    side_sidewalks = query_sidewalks[query_sidewalks.intersects(st_buffer)]

    return side_sidewalks


def crossing_from_dist(street, dist, sidewalks_left, sidewalks_right):
    # Grab a point along the outgoing street
    point = street.interpolate(dist)

    # Find the closest left and right points
    def closest_line_loc(point, lines_gdf):
        return lines_gdf.distance(point).sort_values().index[0]

    sw_left = closest_line_loc(point, sidewalks_left)
    sw_right = closest_line_loc(point, sidewalks_right)
    geom_left = sidewalks_left.loc[sw_left].geometry
    geom_right = sidewalks_right.loc[sw_right].geometry
    left = geom_left.interpolate(geom_left.project(point))
    right = geom_right.interpolate(geom_right.project(point))

    # We now have the lines on the left and right sides. Let's now filter
    # and *not* append if either are invalid
    # (1) They cannot cross any other street line
    # (2) They cannot be too far away (MAX_DIST)
    geometry = LineString([left, right])
    crossing = {
        'geometry': geometry,
        'sw_left': sw_left,
        'sw_right': sw_right
    }

    return crossing


def crosses_other_streets(crossing, other_streets):
    for street in other_streets:
        if street.intersects(crossing):
            return True
    return False


def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]
