"""
Finds the least-steep, least-wandering path down a multi-route trail (one
that splits into alternate branches and/or rejoins itself, merged from
several OSM ways by OSMProcessor._merge_multi_route_clusters). Used as the
trail's rating basis the same way an area trail's computed route is (see
area_routes.py), but built directly from the branches' real mapped nodes
rather than a synthetic sampled grid -- so, unlike area_routes.get_area_route,
the result isn't smoothed, and there's no neighbor-radius proximity search
needed to build the graph: each branch is already an ordered chain of real
edges, and branches that share an endpoint (a fork or rejoin point) share
the exact same coordinate there, since space_line_points_evenly always
keeps a line's first/last input vertex exactly.
"""

import json
from collections import defaultdict
from itertools import pairwise
from math import atan, degrees

import haversine as hs
import numpy as np
import shapely

from core.support.route_search import (
    MAX_GROWTH_MULTIPLIER,
    START_SLOPE_DEGREES,
    STEP_DEGREES,
    Adjacency,
    Point,
    add_virtual_endpoints,
    bottleneck_dijkstra,
    find_best_max_slope,
)

# Unlike an area trail's sampled polygon rim (where a band of near-top/
# near-bottom candidates makes sense -- there's no single meaningful
# "endpoint" on a synthetic grid), a multi-route trail's end candidates are
# restricted to its real dead-end (degree-1) nodes -- see _terminal_indices
# -- so elevation never overrides real topology (a trail that flattens or
# kicks up slightly right before its actual end shouldn't get cut short
# just because an earlier point was the elevation extreme). The start has
# no such restriction (see get_multi_route) -- a run's top is often a fork,
# not a mapped dead end. 0.0 here only matters among each side's own
# candidate pool (or as a fallback when the end's pool has no true dead
# end, e.g. a closed loop), so each side still always resolves to a single
# real point rather than a "close enough" nearby one.
VERTICAL_BAND_FRACTION = 0.0


def _build_graph(branches: list[list[Point]]) -> tuple[list[Point], Adjacency]:
    """
    Flattens every branch's points into one node list, deduping points
    that share an exact (lon, lat) -- a fork/rejoin junction lands on the
    same coordinate in every branch that touches it -- into a single graph
    node, then connects consecutive points within each branch as edges.
    Points with no elevation (a failed lookup) are dropped, same as
    area_routes.get_area_route.
    """
    node_index: dict[tuple[float, float], int] = {}
    nodes: list[Point] = []

    def node_id(point: Point) -> int:
        key = (point[0], point[1])
        idx = node_index.get(key)
        if idx is None:
            idx = len(nodes)
            node_index[key] = idx
            nodes.append(point)
        return idx

    adjacency: Adjacency = defaultdict(list)

    for branch in branches:
        valid_points = [p for p in branch if p[2] is not None]
        for previous_point, point in pairwise(valid_points):
            i, j = node_id(previous_point), node_id(point)
            if i == j:
                continue
            dist = hs.haversine(
                (previous_point[1], previous_point[0]),
                (point[1], point[0]),
                unit=hs.Unit.METERS,
            )
            if dist == 0:
                continue
            rise = point[2] - previous_point[2]
            slope = abs(degrees(atan(rise / dist)))
            adjacency[i].append((j, dist, slope))
            adjacency[j].append((i, dist, slope))

    return nodes, adjacency


def _terminal_indices(adjacency: Adjacency, n_nodes: int) -> list[int]:
    """
    Returns the indices of every dead-end (degree-1) node -- a node with
    exactly one graph edge, i.e. a branch's real, mapped first/last point.
    An ordinary pass-through point (including a place the trail happens to
    cross a different, unrelated trail) always has degree >= 2 and is
    never a candidate, regardless of its elevation. Used only for the
    route's end candidates (see get_multi_route) -- unlike the start, a
    run's bottom is reliably a real runout/dead end, so pinning the end to
    one protects against the route stopping early at a local elevation dip
    that isn't the trail's real topological end.

    Falls back to every node when fewer than 2 qualify -- a closed loop
    has none, and a "lollipop" (one spur feeding into an otherwise
    unbroken loop) has exactly one, which would otherwise make that single
    node both the start and end candidate (add_virtual_endpoints picks the
    only candidate for each side when nothing meets its elevation
    threshold), collapsing the route to zero real points. Falling back to
    every node instead lets start/end still resolve to two different
    (elevation-based) nodes whenever the graph has more than one at all.
    """
    terminals = [i for i in range(n_nodes) if len(adjacency.get(i, [])) == 1]
    return terminals if len(terminals) >= 2 else list(range(n_nodes))


def get_multi_route(
    branches: list[list[Point]],
    vertical_band_fraction: float = VERTICAL_BAND_FRACTION,
    start_slope: float = START_SLOPE_DEGREES,
    step: float = STEP_DEGREES,
    max_growth_multiplier: float = MAX_GROWTH_MULTIPLIER,
) -> dict[str, str]:
    """
    Accepts a multi-route trail's branches (each a list of already
    elevation-populated (lon, lat, elevation) points, in OSM way order)
    and returns a geojson LineString blob for the least-steep,
    least-wandering path from the network's highest point to its lowest
    dead end. See core.support.route_search for the shared bottleneck/
    least-wandering algorithm this reuses.

    The two ends are treated asymmetrically. The end is restricted to real
    dead-end (degree-1) nodes -- see _terminal_indices -- not just the
    lowest elevation, so the route always reaches a branch's actual last
    point even if that isn't the network's elevation minimum (e.g. the
    trail flattens, or kicks up slightly, right before its real end). The
    start has no such restriction: a run's top is frequently a fork where
    two or more branches diverge from one shared point rather than a
    mapped dead end (a lift drop-off, say), so the route always starts at
    the single highest-elevation node in the whole network, on whichever
    branch(es) touch it, even when that node's degree is 2+.

    Raises if no valid route can be found (e.g. the branches don't form a
    connected graph).
    """
    nodes, adjacency = _build_graph(branches)
    node_elev = np.array([p[2] for p in nodes])
    n_nodes = len(nodes)
    terminal_indices = _terminal_indices(adjacency, n_nodes)

    virtual_start_idx, virtual_end_idx = add_virtual_endpoints(
        adjacency, node_elev, range(n_nodes), terminal_indices, vertical_band_fraction
    )
    n_nodes_with_virtual = n_nodes + 2

    bottleneck = bottleneck_dijkstra(adjacency, virtual_start_idx, n_nodes_with_virtual)
    slope_limit = bottleneck[virtual_end_idx]

    best = find_best_max_slope(
        adjacency,
        virtual_start_idx,
        virtual_end_idx,
        n_nodes_with_virtual,
        slope_limit,
        start_slope=start_slope,
        step=step,
        max_growth_multiplier=max_growth_multiplier,
    )
    if best is None:
        raise ValueError(
            "No route connects a valid start point to a valid end point even at "
            f"the loosest slope cap ({start_slope} degrees) -- the branches may "
            "not form a connected graph."
        )
    _max_slope, route_indices, _route_length_m = best

    route_indices = route_indices[1:-1]  # drop the virtual start/end bridging nodes
    route_points = [nodes[i] for i in route_indices]

    return json.loads(shapely.to_geojson(shapely.LineString(route_points)))
