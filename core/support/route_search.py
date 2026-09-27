"""
Generic "lowest max pitch, tie-broken by least wandering" path search over
a weighted graph -- shared by area_routes.py (a glade/bowl's sampled
polygon grid) and multi_route.py (a branching trail's real mapped nodes).
Neither module's graph-*building* step lives here, since that part is
specific to each caller's geometry; only the search itself is generic.

Runs in two phases over a caller-supplied adjacency graph:

1. Bottleneck pass: a modified Dijkstra where a path's cost is its worst
   edge, not the sum of edges, run from a virtual start node (connected to
   every candidate point near the top of the graph's vertical drop) to a
   virtual end node (connected from every candidate point near the
   bottom). This finds the gentlest steepest-pitch achievable by any valid
   start/end combination, rather than pinning to the single highest and
   lowest points.
2. Least-wandering pass: starting from a loose slope cap and tightening
   it toward the bottleneck minimum, tracks route length at each cap
   against a fixed baseline (the loosest pass). Stops as soon as
   tightening further would grow the route beyond a fixed multiple of
   that baseline, and keeps the previous, still-affordable cap.
"""

import heapq

import numpy as np

VERTICAL_BAND_FRACTION = 0.05  # points within this fraction of the vertical drop from the top/bottom are valid start/end candidates
START_SLOPE_DEGREES = 70  # loosest slope cap the least-wandering pass starts from
STEP_DEGREES = 1  # how far each tightening step lowers the slope cap
MAX_GROWTH_MULTIPLIER = 1.2  # max route-length growth vs. loosest pass

Point = tuple[float, float, float]  # (lon, lat, elevation)
# node index -> [(neighbor index, distance_m, slope_deg), ...]
Adjacency = dict[int, list[tuple[int, float, float]]]


def bottleneck_dijkstra(adjacency: Adjacency, start: int, n_nodes: int) -> list[float]:
    """
    Modified Dijkstra where a path's cost is its single worst edge rather
    than the sum of edges -- finds the minimum steepest-pitch needed to
    reach each node from `start`.
    """
    bottleneck = [float("inf")] * n_nodes
    bottleneck[start] = 0.0
    visited = [False] * n_nodes
    heap = [(0.0, start)]

    while heap:
        cost, u = heapq.heappop(heap)
        if visited[u]:
            continue
        visited[u] = True
        for v, _dist, slope in adjacency[u]:
            candidate = max(cost, slope)
            if candidate < bottleneck[v]:
                bottleneck[v] = candidate
                heapq.heappush(heap, (candidate, v))

    return bottleneck


def add_virtual_endpoints(
    adjacency: Adjacency,
    node_elev: np.ndarray,
    start_indices,
    end_indices,
    vertical_drop_fraction: float,
) -> tuple[int, int]:
    """
    Adds two virtual nodes to `adjacency` (indices len(node_elev) and
    len(node_elev) + 1): a virtual start with zero-cost edges to every
    candidate point within the top `vertical_drop_fraction` of the graph's
    elevation range, and a virtual end with zero-cost edges FROM every
    candidate point within the bottom `vertical_drop_fraction`. This lets
    the route search treat any high/low-enough point as a valid
    start/end, rather than pinning to the single highest/lowest point.
    Mutates real nodes' adjacency lists (for the end side).

    Start candidates are restricted to `start_indices`, end candidates to
    `end_indices` -- separate pools, since the two sides don't need the
    same restriction. Area trails pass the same polygon rim
    (range(n_boundary)) for both. A multi-route trail passes every node for
    the start (a run's top is often a fork where branches diverge from a
    shared point, not a mapped dead end -- see multi_route.py) but only its
    dead-end (degree-1) nodes for the end, so the route still always ends
    at a branch's real endpoint rather than wherever happens to be the
    lowest point along the way.

    The vertical_drop_fraction threshold is based on the elevation range
    across *all* nodes (both pools + any node in neither), so it's possible
    for no candidate to qualify -- e.g. an interior knob taller than the
    entire rim. When that happens, falls back to just the single
    highest/lowest candidate in that pool, so there's always at least one
    valid start/end.

    Returns (virtual_start_idx, virtual_end_idx).
    """
    n_nodes = len(node_elev)
    virtual_start_idx = n_nodes
    virtual_end_idx = n_nodes + 1

    start_indices = list(start_indices)
    end_indices = list(end_indices)

    vertical_drop = node_elev.max() - node_elev.min()
    top_threshold = node_elev.max() - vertical_drop_fraction * vertical_drop
    bottom_threshold = node_elev.min() + vertical_drop_fraction * vertical_drop

    start_candidates = [i for i in start_indices if node_elev[i] >= top_threshold]
    end_candidates = [i for i in end_indices if node_elev[i] <= bottom_threshold]

    if not start_candidates:
        start_candidates = [max(start_indices, key=lambda i: node_elev[i])]
    if not end_candidates:
        end_candidates = [min(end_indices, key=lambda i: node_elev[i])]

    for i in start_candidates:
        adjacency[virtual_start_idx].append((i, 0.0, 0.0))
    for i in end_candidates:
        adjacency[i].append((virtual_end_idx, 0.0, 0.0))

    return virtual_start_idx, virtual_end_idx


def least_wandering_path(
    adjacency: Adjacency,
    start: int,
    end: int,
    n_nodes: int,
    slope_limit: float,
    epsilon: float = 1e-6,
) -> tuple[list[int], float]:
    """
    Among all routes whose steepest single segment is at or below
    `slope_limit`, find the shortest one (fewest unnecessary detours).
    Returns (None, None) if no such route exists.
    """
    dist_cost = [float("inf")] * n_nodes
    dist_cost[start] = 0.0
    prev = [None] * n_nodes
    visited = [False] * n_nodes
    heap = [(0.0, start)]

    while heap:
        cost, u = heapq.heappop(heap)
        if visited[u]:
            continue
        visited[u] = True
        if u == end:
            break
        for v, dist, slope in adjacency[u]:
            if slope > slope_limit + epsilon:
                continue
            candidate = cost + dist
            if candidate < dist_cost[v]:
                dist_cost[v] = candidate
                prev[v] = u
                heapq.heappush(heap, (candidate, v))

    if dist_cost[end] == float("inf"):
        return None, None

    path = []
    node = end
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path, dist_cost[end]


def find_best_max_slope(
    adjacency: Adjacency,
    start: int,
    end: int,
    n_nodes: int,
    slope_limit: float,
    start_slope: float,
    step: float,
    max_growth_multiplier: float,
) -> tuple[float, list[int], float]:
    """
    Starts from a loose `start_slope` cap and tightens it toward the
    bottleneck minimum (`slope_limit`) in `step`-degree increments,
    tracking route length at each cap against a fixed baseline: the route
    length at `start_slope` (the first, loosest pass). Stops -- and
    returns the previous cap -- as soon as a route's length exceeds
    `max_growth_multiplier` times that baseline, since it was the last cap
    still within budget of the original length.

    Returns None if no route exists even at `start_slope`.
    """
    slope_values = []
    s = start_slope
    while s > slope_limit:
        slope_values.append(s)
        s -= step
    slope_values.append(slope_limit)

    best = None  # (max_slope, route_indices, route_length_m)
    baseline_length_m = None

    for max_slope in slope_values:
        route_indices, route_length_m = least_wandering_path(
            adjacency, start, end, n_nodes, max_slope
        )
        if route_indices is None:
            break

        if baseline_length_m is None:
            baseline_length_m = route_length_m
        elif route_length_m > baseline_length_m * max_growth_multiplier:
            break

        best = (max_slope, route_indices, route_length_m)

    return best
