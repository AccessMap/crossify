import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point


def make_crossings(intersections_dict, sidewalks):
    crs = sidewalks.crs
    st_crossings = []
    ixn_dat = []
    for i, (ixn, data) in enumerate(intersections_dict.items()):
        ixn_dat.append({
            'geometry': data['geometry'],
            'ixn': i
        })
        for street in data['streets']:
            new_crossing = make_crossing(street, sidewalks, data['streets'])
            if new_crossing is not None:
                st_crossings.append({
                    'geometry': new_crossing['crossing'],
                    'too_long': new_crossing['too_long'],
                    'crosses_self': new_crossing['crosses_self'],
                    'crosses_others': new_crossing['crosses_others'],
                    'ixn': i
                })
    st_crossings = gpd.GeoDataFrame(st_crossings)
    st_crossings = st_crossings[st_crossings.type == 'LineString']
    st_crossings = st_crossings[st_crossings.is_valid]

    # Remove duplicates
    def cmp(geom):
        p1 = np.round(geom.coords[0], 2)
        p2 = np.round(geom.coords[-1], 2)
        return str([p1, p2])

    comparison = st_crossings.geometry.apply(cmp)
    comparison.name = 'cmp'
    unique = st_crossings.groupby(comparison).first()
    st_crossings = gpd.GeoDataFrame(unique.reset_index())
    st_crossings.crs = crs

    st_crossings = st_crossings.to_crs({'init': 'epsg:4326'})

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

    # FIXME: use 'z layer' data if available (e.g. OSM)

    START_DIST = 4
    INCREMENT = 2
    MAX_DIST_ALONG = 25
    MAX_CROSSING_DIST = 30

    st_distance = min(street.length / 2, MAX_DIST_ALONG)
    start_dist = min(START_DIST, st_distance / 2)

    lines = []
    for dist in np.arange(start_dist, st_distance, INCREMENT):
        # Grab a point along the outgoing street
        point = street.interpolate(dist)
        # Extract the street line segment associated with the point (i.e. if
        # the street has several segments, get just one, described by 2 points)
        coords = street.coords
        for i in range(len(coords) - 1):
            segment = LineString((coords[i], coords[i + 1]))
            if segment.distance(point) < 1e-8:
                break
        point_l, point_r = closest_point_right_left(point, segment, sidewalks)
        if point_l is None or point_r is None:
            # Skip! Didn't find points on right/left
            continue

        # We now have the lines on the left and right sides. Let's now filter
        # and *not* append if either are invalid
        # (1) They cannot cross any other street line
        # (2) They cannot be too far away (MAX_DIST)
        crossing = LineString([point_l, point_r])

        # if side.length > MAX_DIST or crosses_streets(side, streets):
        too_long = False
        if crossing.length > MAX_CROSSING_DIST:
            too_long = True
        other_streets = [st for st in streets_list if st != street]
        street_cut = cut(street, st_distance)[0]
        crosses_self, crosses_others = valid_crossing(crossing, street_cut,
                                                      other_streets)

        # The sides have passed the filter! Add their data to the list
        if crosses_self and not crosses_others and not too_long:
            lines.append({
                'distance': dist,
                'crossing': crossing,
                'too_long': str(too_long),
                'crosses_self': str(crosses_self),
                'crosses_others': str(crosses_others),
                'street': street_cut
            })

    if not lines:
        return None

    # Return the shortest crossing.
    # TODO: Should also bias towards *earlier* appearances, i.e. towards
    # corner.
    # lengths = np.array([line['crossing'].length for line in lines])
    # # Inverse distance function (distance from intersection)
    # distance_metric = 1 / np.array([line['distance'] for line in lines])

    # lengths * distance_metric
    def metric(crossing):
        return crossing['crossing'].length + 1e-1 * crossing['distance']

    return sorted(lines, key=metric)[0]


def side_of_segment(point, segment):
    '''Given a point and a line segment, determine which side of the line the
    point is on (from perspective of the line). Returns 0 if the point is
    exactly on the line (very unlikely given floating point math), 1 if it's
    on the right, and -1 if it's on the left.

    :param point: Point on some side of a line segment.
    :type point: shapely.geometry.Point
    :param segment: Line segment made up of only two points.
    :type segment: shapely.geometry.LineString
    :returns: int

    '''
    x, y = point.coords[0]
    (x1, y1), (x2, y2) = segment.coords
    side = np.sign((x - x1) * (y2 - y1) - (y - y1) * (x2 - x1))

    return side


def closest_point_right_left(point, segment, sidewalks):
    # Get the 10 closest sidewalks (bounding box closeness)
    query = sidewalks.sindex.nearest(point.bounds, 10, objects=True)
    sidewalk_ids = [x.object for x in query]
    # TODO: this is a fairly slow step. Idea:
    # Use a representative point to ask the 'left or right side' question first
    # so there's no need to calculate distance / make a line if that side
    # already has a point
    sw_geoms = sidewalks.geometry.loc[sidewalk_ids]
    sw_distances = sw_geoms.distance(point)
    sorted_sw_geoms = sw_geoms.loc[sw_distances.sort_values().index]

    left = None
    right = None

    for idx, geom in sorted_sw_geoms.iteritems():
        closest_point = geom.interpolate(geom.project(point))
        side = side_of_segment(closest_point, segment)
        if (left and side < 0) or (right and side >= 0):
            # We've already found a sidewalk for this side
            continue
        if side < 0:
            left = closest_point
        else:
            right = closest_point

    return left, right


def valid_crossing(crossing, street, other_streets):
    crosses_street = street.intersects(crossing)
    # if not crosses_street:
    #     return False
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
