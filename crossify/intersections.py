from shapely.geometry import LineString, Point


def group_intersections(G):
    # FIXME: require undirected graph for degree calcs

    # Isolate intersections for which to generate crossings
    intersections = [node for node, degree in G.degree if degree > 2]

    # Find all incoming and outgoing streets, associate them with the
    # intersection, and make sure the geometries all extend out from the node
    intersection_groups = {}

    for intersection_id in intersections:
        data = G.node[intersection_id]
        intersection = Point(data['x'], data['y'])

        # Two-way streets will produce two edges: one in, one out. We will keep
        # only the outgoing one
        incoming = set(G.predecessors(intersection_id))
        outgoing = set(G.successors(intersection_id))
        incoming = incoming.difference(outgoing)

        geometries = []
        for node in incoming:
            geometries.append(get_edge_geometry(G, node, intersection_id))

        for node in outgoing:
            geometries.append(get_edge_geometry(G, intersection_id, node))

        for i, geometry in enumerate(geometries):
            if Point(*geometry.coords[-1]).distance(intersection) < 1e-1:
                geometries[i] = LineString(geometry.coords[::-1])

        intersection_groups[intersection_id] = {
            'geometry': intersection,
            'streets': geometries
        }

    return intersection_groups


def get_edge_geometry(G, from_node, to_node):
    edge = G[from_node][to_node][0]
    if 'geometry' in edge:
        return edge['geometry']
    else:
        start = Point((G.nodes[from_node]['x'], G.nodes[from_node]['y']))
        end = Point((G.nodes[to_node]['x'], G.nodes[to_node]['y']))
        return LineString([start, end])
