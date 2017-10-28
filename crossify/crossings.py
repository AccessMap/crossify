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

    # FIXME: use 'z layer' data if available (e.g. OSM)

    lines = []
    MAX_DIST_ALONG = 20
    MAX_DIST = 25

    st_distance = min(street.length / 2, MAX_DIST_ALONG)
    street_cut = cut(street, st_distance)[0]

    for dist in np.arange(1e-6, st_distance, 1):
        point = street.interpolate(dist)
        coords = street.coords
        for i in range(len(coords) - 1):
            segment = LineString((coords[i], coords[i + 1]))
            if segment.distance(point) < 1e-8:
                break
        left_line, right_line = closest_line_right_left(point, segment,
                                                        sidewalks)
        if left_line is None or right_line is None:
            # Skip! Didn't find lines on right/left
            continue

        # We now have the lines on the left and right sides. Let's now filter
        # and *not* append if either are invalid
        # (1) They cannot cross any other street line
        # (2) They cannot be too far away (MAX_DIST)
        crossing = LineString([left_line.coords[-1], right_line.coords[-1]])

        # if side.length > MAX_DIST or crosses_streets(side, streets):
        too_long = False
        if crossing.length > MAX_DIST:
            too_long = True
        other_streets = [st for st in streets_list if st != street]
        crosses_self, crosses_others = valid_crossing(crossing, street_cut,
                                                      other_streets)
#         if not valid_crossing(side, street, streets_list):
#             invalid = 'yes'

        # The sides have passed the filter! Add their data to the list
        if crosses_self and not crosses_others and not too_long:
            lines.append({
                'distance': dist,
                'left': left_line,
                'right': right_line,
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


def closest_line_right_left(point, segment, sidewalks):
    # Get the 10 closest sidewalks (bounding box closeness)
    query = sidewalks.sindex.nearest(point.bounds, 10, objects=True)
    sidewalk_ids = [x.object for x in query]
    # TODO: this is a fairly slow step. Idea:
    # Use a representative point to ask the 'left or right side' question first
    # so there's no need to calculate distance / make a line if that side
    # already has a point

    # Draw a line from the point on the street to each sidewalk, evaluate
    def draw_half_line(point, sidewalk_geom):
        sidewalk = sidewalks.loc[sidewalk_id, 'geometry']
        distance_along_sidewalk = sidewalk.project(point)
        sw_point = sidewalk.interpolate(distance_along_sidewalk)
        half_line = LineString([point.coords[0], sw_point.coords[0]])
        return half_line

    half_lines = []
    for sidewalk_id in sidewalk_ids:
        sidewalk_geom = sidewalks.loc[sidewalk_id, 'geometry']
        half_line = draw_half_line(point, sidewalk_geom)
        half_lines.append(half_line)

    half_lines = sorted(half_lines, key=lambda x: x.length)

    # Loop over each line until left/right are found
    left = None
    right = None

    for line in half_lines:
        if left is not None and right is not None:
            break
        side = side_of_segment(Point(line.coords[-1]), segment)
        if side < 0:
            # Point is on left side
            if left is None:
                left = line
            else:
                continue
        else:
            # Point is on the right side
            if right is None:
                right = line
            else:
                continue

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
