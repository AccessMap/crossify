import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point, Polygon


def make_crossings(intersections_dict, sidewalks, debug=False):
    crs = sidewalks.crs
    st_crossings = []
    street_segments = []
    ixn_dat = []
    for i, (ixn, data) in enumerate(intersections_dict.items()):
        ixn_dat.append({
            'geometry': data['geometry'],
            'ixn': i
        })
        for street in data['streets']:
            new_crossing = make_crossing(street, sidewalks, data['streets'],
                                         debug)
            if debug:
                new_crossing, street_segment = new_crossing
                street_segments.append(street_segment)
            if new_crossing is not None:
                st_crossings.append(new_crossing)

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

    if debug:
        street_segments = gpd.GeoDataFrame(street_segments)
        street_segments.crs = sidewalks.crs
        return st_crossings, street_segments
    else:
        return st_crossings


def make_crossing(street, sidewalks, streets_list, debug=False):
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

    # FIXME: use 'z layer' data if available (e.g. OSM)

    START_DIST = 4
    INCREMENT = 2
    MAX_DIST_ALONG = 25
    MAX_CROSSING_DIST = 30
    OFFSET = MAX_CROSSING_DIST / 2

    st_distance = min(street.length / 2, MAX_DIST_ALONG)
    start_dist = min(START_DIST, st_distance / 2)

    # Create buffer for the street search area, one for each side, then find
    # the sidewalks intersecting that buffer - use as candidates for
    # right/left
    street_cut = cut(street, st_distance)[0]

    if debug:
        street_segment = {'geometry': street_cut, 'issue': 'None'}

    sides = {}

    for side in ('left', 'right'):
        side_sidewalks = get_side_sidewalks(OFFSET, side, street_cut,
                                            sidewalks)
        if side_sidewalks.shape[0] < 1:
            # One of the sides has no sidewalks to connect to! Abort!
            if debug:
                street_segment['issue'] = 'no {} sidewalk'.format(side)
                return None, street_segment
            else:
                return None
        sides[side] = side_sidewalks

    candidates = []
    for dist in np.arange(start_dist, st_distance, INCREMENT):
        crossing, sw_left, sw_right = crossing_from_dist(street, dist,
                                                         sides['left'],
                                                         sides['right'])

        # We now have the lines on the left and right sides. Let's now filter
        # and *not* append if either are invalid

        # if side.length > MAX_DIST or crosses_streets(side, streets):
        other_streets = [st for st in streets_list if st != street]
        crosses_self, crosses_others = valid_crossing(crossing, street_cut,
                                                      other_streets)

        # The sides have passed the filter! Add their data to the list
        if crosses_self and not crosses_others:
            candidates.append({
                'geometry': crossing,
                'distance': dist,
                'sw_left': sw_left,
                'sw_right': sw_right
            })

    if not candidates:
        if debug:
            street_segment['issue'] = 'no candidates'
            return None, street_segment
        else:
            return None

    # Return the shortest crossing.
    # TODO: Should also bias towards *earlier* appearances, i.e. towards
    # corner.
    # lengths = np.array([line['crossing'].length for line in lines])
    # # Inverse distance function (distance from intersection)
    # distance_metric = 1 / np.array([line['distance'] for line in lines])

    # lengths * distance_metric
    def metric(candidate):
        return candidate['geometry'].length + 1e-1 * candidate['distance']

    best = sorted(candidates, key=metric)[0]

    if debug:
        return best, street_segment
    else:
        return best


def get_side_sidewalks(offset, side, street, sidewalks):
    offset = street.parallel_offset(offset, side, 0, 1, 1)
    if offset.type == 'MultiLineString':
        # Convert to LineString
        coords = []
        for geom in offset.geoms:
            coords += list(geom.coords)
        offset = LineString(coords)
    if side == 'left':
        offset.coords = offset.coords[::-1]
    st_buffer = Polygon(list(street.coords) +
                        list(offset.coords) +
                        [street.coords[0]])
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
    crossing = LineString([left, right]), sw_left, sw_right

    return crossing


def valid_crossing(crossing, street, other_streets):
    crosses_street = street.intersects(crossing)
    crosses_others = [other.intersects(crossing) for other in other_streets]

    return crosses_street, any(crosses_others)

    if any(crosses_others):
        return False

    return True


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
