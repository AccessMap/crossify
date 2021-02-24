import numpy as np
from shapely.geometry import LineString, Point


def group_intersections(G):
    # FIXME: require undirected graph for degree calcs

    # Isolate intersections for which to generate crossings
    intersections = [node for node, degree in G.degree if degree > 2]

    # Find all incoming and outgoing streets, associate them with the
    # intersection, and make sure the geometries all extend out from the node
    intersection_groups = {}

    for intersection_id in intersections:
        data = G.nodes[intersection_id]
        intersection = Point(data["x"], data["y"])

        # Two-way streets will produce two edges: one in, one out. We will keep
        # only the outgoing one
        incoming = set(G.predecessors(intersection_id))
        outgoing = set(G.successors(intersection_id))
        incoming = incoming.difference(outgoing)

        edges = []
        for node in incoming:
            edges.append(get_edge(G, node, intersection_id))

        for node in outgoing:
            edges.append(get_edge(G, intersection_id, node))

        # Make sure all streets radiate out from the intersection
        edges_ordered = []
        for i, edge in enumerate(edges):
            copy = edge.copy()
            point = Point(*edge["geometry"].coords[-1])
            if point.distance(intersection) < 1e-1:
                reversed_street = LineString(edge["geometry"].coords[::-1])
                copy["geometry"] = reversed_street
            edges_ordered.append(copy)

        intersection_groups[intersection_id] = {
            "geometry": intersection,
            "streets": edges_ordered,
        }

    return intersection_groups


def get_edge(G, from_node, to_node):
    edge = G[from_node][to_node][0]

    if "geometry" not in edge:
        start = Point((G.nodes[from_node]["x"], G.nodes[from_node]["y"]))
        end = Point((G.nodes[to_node]["x"], G.nodes[to_node]["y"]))
        edge["geometry"] = LineString([start, end])

    if "layer" in edge:
        if edge["layer"] is np.nan:
            edge["layer"] = 0
    else:
        edge["layer"] = 0

    return edge
