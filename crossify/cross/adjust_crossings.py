import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import geometry
from . import helpers

CORNER_CROSSING_MATCH_DISTANCE = 4
CORNER_MID_MATCH_DISTANCE = 2.5
EPS = 1e-15

# this is to fix the issue of not connecting T intersection or non corner crossings to sidewalks
# they need a shared node on the sidewalk for it to merge in osmizer
def add_endpoints_to_sidewalks(sidewalks, crossings):
    sidewalks['id'] = sidewalks.index
    cross_ends = []
    ends = []
    not_found = []
    shapes = []
    for row in crossings.iterrows():
        points = row[1].geometry.coords
        ends.append(points[0])
        ends.append(points[-1])

    # iterate over ever crossing endpoint
    count = 0
    for point in ends:
        pnt_shply = geometry.Point(point)
        # find closest sidewalk
        matches = sidewalks.sindex.nearest(point, 1, objects=True)
        match = sidewalks.loc[list(matches)[0].object]
        match_points = list(match.geometry.coords)
        # find where it falls on the line
        temp_line = geometry.LineString([match_points[0], match_points[1]])
        min_dist = pnt_shply.distance(temp_line)
        min_index = 1
        # fencepost min
        for x in range(2, len(match_points)):
            temp_line = geometry.LineString([match_points[x - 1], match_points[x]])
            dist = pnt_shply.distance(temp_line)
            if dist < min_dist:
                min_index = x
        if min_dist >= EPS: # these are non corner crossings
            match_points.insert(min_index, point)
            cross_ends.append(pnt_shply)
            new_match = geometry.LineString(match_points)
            match.geometry = new_match
            # update geometry with point added
            sidewalks.iloc[match['id']] = match
    return sidewalks
    

def generate_corner_ramps(sidewalks, corner_crossing_mid_points):
    corner_crossing_mid_points['id'] = corner_crossing_mid_points.index
    seen_it = set()
    corners = helpers.get_corners(sidewalks)
    corner_ramps = []
    for corner_row in corners.iterrows():
        point = corner_row[1]['geometry']
        buff = point.buffer(CORNER_MID_MATCH_DISTANCE)
        inter = corner_crossing_mid_points.sindex.intersection(buff.bounds, objects=True)
        ids = [x.object for x in inter]
        bbox_ixn = corner_crossing_mid_points.loc[ids]
        for match_row in bbox_ixn.iterrows():
            if match_row[1]['id'] not in seen_it:
                line = geometry.LineString([point, match_row[1]['geometry']])
                corner_ramps.append(line)
                seen_it.add(match_row[1]['id'])

    results = split_corner_ramp(corner_ramps)
    return results


# adjust crossing location to be the specified distance from the corner creating three nodes
# where sidewalk ways meet at a corner allowing the editing process to be easier.
def generate_crossing_offset(sidewalks, crossings, link_offset_from_corner=0.5):
    # method
    # 1) generate endpoints link_offset from corner and slope of swk
    # 2) find crossings that intersect link_offset + 1
    # 3) if crossing slope roughly orthogonal to swk slope
    # 4) new end point swap with crossing endpoint

    # returns the endpoint in the crossing that is furthest from the given point
    def find_furthest_endpoint(crossing, point):
        coords = crossing.geometry.coords
        end1 = geometry.Point(coords[0])
        end2 = geometry.Point(coords[1])
        distance1 = point.distance(geometry.Point(end1))
        distance2 = point.distance(geometry.Point(end2))
        if distance1 == distance2:
            raise ValueError("DISTANCES ARE EQUAL")
        elif distance1 < distance2: 
            return end2
        else:
            return end1


    def adjust_crossing_ends(crossing_ways, points):
        points['buffer'] = points.geometry.apply(lambda x: x.buffer(link_offset_from_corner + 1))
        for row in points.iterrows():
            point = row[1]
            inter = crossing_ways.sindex.intersection(point['buffer'].bounds, objects=True)
            ids = [x.object for x in inter]
            bbox_ixn = crossing_ways.loc[ids]
            for crossing_row in bbox_ixn.iterrows():
                crossing_option = crossing_row[1]
                if helpers.is_orthagonal(crossing_option['slope'], point['sw_slope']):
                    # TODO: We could get two orthagonal crossings from the same point
                    further_crossing_endpoint = find_furthest_endpoint(crossing_option, point['geometry'])
                    new_crossing = geometry.LineString([point['geometry'], further_crossing_endpoint])
                    crossing_ways.set_value(crossing_option['id'], 'geometry', new_crossing)

        return crossing_ways

    crossings['id'] = crossings.index
    crossings.sindex
    starts = sidewalks.geometry.apply(lambda x: x.interpolate(link_offset_from_corner))
    starts_slope = sidewalks.geometry.apply(lambda x: helpers.azimuth(x.coords[0], x.coords[1]))
    ends   = sidewalks.geometry.apply(lambda x: x.interpolate(x.length - link_offset_from_corner))
    ends_slope = sidewalks.geometry.apply(lambda x: helpers.azimuth(x.coords[-2], x.coords[-1]))
    crossings['slope']  = crossings.geometry.apply(lambda x: helpers.azimuth(x.coords[0], x.coords[-1]))

    starts = gpd.GeoDataFrame({
        'sw_slope': starts_slope,
        'geometry': starts
    })

    ends = gpd.GeoDataFrame({
        'sw_slope': ends_slope,
        'geometry': ends
    })

    crossings = adjust_crossing_ends(crossings, ends)
    crossings = adjust_crossing_ends(crossings, starts)

    # hackey way to add points to sidewalks
    sidewalks['id'] = sidewalks.index
    starts['id'] = starts.index
    ends['id'] = ends.index

    # Modify sidewalks to contain new points
    for row in sidewalks.iterrows():
        sidewalk = row[1]
        points = list(sidewalk.geometry.coords)
        start_coords = starts.iloc[sidewalk['id']].geometry.coords
        points.insert(1, start_coords[0])
        end_coords = ends.iloc[sidewalk['id']].geometry.coords
        points.insert(len(points) - 1, end_coords[0])
        new_sidewalk = geometry.LineString(points)
        sidewalks.set_value(sidewalk['id'], 'geometry', new_sidewalk)

    return {'crossings': crossings, 'sidewalks': sidewalks}

# splits coner ramp into link, ramp, crossing
# corner ramps raw assume sidewalk end point is first in linestring
def split_corner_ramp(corner_ramps_raw):
    crossings = []
    links = []
    lowered_curbs = []
    for ramp in corner_ramps_raw:
        geom = ramp
        swk_end = geometry.Point(geom.coords[0])
        curb = geom.interpolate(geom.length / 2)
        crossing_end = geometry.Point(geom.coords[-1])
        crossings.append(geometry.LineString([curb, crossing_end]))
        links.append(geometry.LineString([swk_end, curb]))
        lowered_curbs.append(curb)
    return {'crossings': crossings, 'links': links, 'lowered_curbs': lowered_curbs}

# splits crossings at supposed curb distance and makes the curp portion a sidewalk link
# returns a tuple (crossings, link, raised_curbs) where links anre the segment that join 
# sidewalks to street crossings and the point where they meet is returned as a raised curb
# links are always returned with the sidewalk side end node first
def split_crossings(crossings_full, link_distance=1, crossing_node_distance=2.5):
    crossings = []
    links = []
    raised_curbs = []
    crossing_snips = []
    for row in crossings_full.iterrows():
        geom = row[1]['geometry']
        end1 = geometry.Point(geom.coords[0])
        end2 = geometry.Point(geom.coords[-1])
        curb1 = geom.interpolate(link_distance)
        curb2 = geom.interpolate(geom.length - link_distance)

        # data for corner crossing generation
        crossing_node1 = geom.interpolate(crossing_node_distance)
        crossing_node2 = geom.interpolate(geom.length - crossing_node_distance)
        crossing_snips.append(geometry.LineString([crossing_node1, crossing_node2]))

        crossings.append(geometry.LineString([curb1, crossing_node1, crossing_node2, curb2]))
        links.append(geometry.LineString([end1, curb1]))
        links.append(geometry.LineString([end2, curb2]))
        raised_curbs.append(curb1)
        raised_curbs.append(curb2)

    extra_crossings = generate_corner_crossings(crossing_snips)
    crossings.extend(extra_crossings['corner_crossings'])

    return {'crossings': crossings, 'links': links, 'raised_curbs': raised_curbs, 'corner_crossing_nodes': extra_crossings['mids']}

# returns corner crossing and mids (midpoint) of crossing
# when two crossing nodes are close to each other and the angle between the crossings is around 90 degrees
def generate_corner_crossings(crossings_snips):
    nodes = []
    slopes = []
    for snip in crossings_snips:
        end1 = snip.coords[0]
        end2 = snip.coords[-1]
        nodes.append(geometry.Point(end1))
        nodes.append(geometry.Point(end2))
        slope = helpers.azimuth(end1, end2)
        slopes.append(slope)
        slopes.append(slope)

    nodes = gpd.GeoDataFrame({'slope': slopes, 'geometry': nodes})

    mids = []
    crossings = []
    nodes['id'] = nodes.index
    nodes.sindex

    seen_it = set()

    for node_row in nodes.iterrows():
        node = node_row[1]['geometry']
        seen_it.add(node_row[1]['id'])

        buff = node.buffer(CORNER_CROSSING_MATCH_DISTANCE)
        inter = nodes.sindex.intersection(buff.bounds, objects=True)
        ids = [x.object for x in inter]
        bbox_ixn = nodes.loc[ids]
        for match_row in bbox_ixn.iterrows():
            match = match_row[1]
            if match['id'] != node_row[1]['id'] and (match['id'] not in seen_it) and helpers.is_orthagonal(match['slope'], node_row[1]['slope']):
                line = geometry.LineString([match['geometry'], node])
                line_mid = line.interpolate(line.length / 2)
                crossings.append(geometry.LineString([match['geometry'], line_mid, node]))
                mids.append(line_mid)

    return {'corner_crossings': crossings, 'mids': mids}