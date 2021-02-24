import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point


def split_sidewalks(sidewalks, crossings, tolerance=1e-1, precision=3):
    """Create a network from (potentially) independently-generated sidewalks
    and other paths. Sidewalks will be split into multiple lines wherever
    their endpoints (nearly) intersect other paths on their same layer, within
    some distance tolerance.

    """
    crossings = crossings.to_crs(sidewalks.crs)
    ends = []
    for idx, row in crossings.iterrows():
        ends.append(Point(np.round(row["geometry"].coords[0], precision)))
        ends.append(Point(np.round(row["geometry"].coords[-1], precision)))

    ends = gpd.GeoDataFrame(geometry=ends)
    ends["wkt"] = ends.geometry.apply(lambda x: x.wkt)
    ends = ends.drop_duplicates("wkt")
    ends = ends.drop("wkt", axis=1)

    splits = []
    for idx, row in sidewalks.iterrows():
        line = row["geometry"]

        # Expand bounds by tolerance to catch everything in range, order is
        # left, bottom, right, top
        bounds = [
            line.bounds[0] - tolerance,
            line.bounds[1] - tolerance,
            line.bounds[2] + tolerance,
            line.bounds[3] + tolerance,
        ]

        hits = list(ends.sindex.intersection(bounds))

        # Now iterate over and filter
        distances_along = []
        for index in hits:
            loc = ends.index[index]
            point = ends.loc[loc, "geometry"]

            # Is the point actually within the tolerance distance?
            if point.distance(line) > tolerance:
                continue

            # Find closest point on line
            distance_along = line.project(point)

            # Did you find an endpoint?
            if (distance_along < 0.01) or (
                distance_along >= (line.length - 0.01)
            ):
                continue

            distances_along.append(distance_along)

        # Split
        lines = []
        line1 = line
        for distance in reversed(sorted(distances_along)):
            line1, line2 = _cut(line1, distance)
            lines.append(line2)

        lines.append(line1)

        for line in lines:
            split = dict(row)
            split["geometry"] = line
            # Ignore incline for short segments near paths - these are
            # usually near intersections and are more flat on average.
            # (8 meters)
            if line.length < 8:
                split["incline"] = 0
            splits.append(split)

    sidewalks_network = gpd.GeoDataFrame(splits)
    sidewalks_network.crs = sidewalks.crs

    return sidewalks_network


def _cut(line, distance):
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)

    pd = 0
    last = coords[0]
    for i, p in enumerate(coords):
        if i == 0:
            continue
        pd += _point_distance(last, p)

        if pd == distance:
            return [LineString(coords[: i + 1]), LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:]),
            ]

        last = p
    cp = line.interpolate(distance)
    return [
        LineString(coords[:i] + [(cp.x, cp.y)]),
        LineString([(cp.x, cp.y)] + coords[i:]),
    ]


def _point_distance(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return (dx ** 2 + dy ** 2) ** 0.5
