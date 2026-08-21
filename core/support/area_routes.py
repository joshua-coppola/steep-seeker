"""
Finds the least-steep, least-wandering ski route down an area trail (a
glade, bowl, or other trail sampled as a polygon rather than a line).

Runs in three phases over a graph built from the area's sampled points
(the boundary ring plus the interior grid, per `polygon_interior_grid`):

1. Bottleneck pass -- a modified Dijkstra where a path's cost is its worst
   edge, not the sum of edges, run from a virtual start node (connected to
   every boundary point near the top of the area's vertical drop) to a
   virtual end node (connected from every boundary point near the bottom).
   This finds the gentlest steepest-pitch achievable by any valid
   start/end combination, rather than pinning to the single highest and
   lowest sampled points.
2. Least-wandering pass -- starting from a loose slope cap and tightening
   it toward the bottleneck minimum, tracks route length at each cap
   against a fixed baseline (the loosest pass). Stops as soon as
   tightening further would grow the route beyond a fixed multiple of
   that baseline, and keeps the previous, still-affordable cap.
3. Smoothing pass -- a basic moving average over the route's lon/lat/
   elevation to reduce the zig-zag that shortest-path tie-breaking leaves
   behind on a lattice-like graph. Endpoints are left untouched. This pass
   is not slope-validated: a smoothed segment isn't guaranteed to stay
   under the chosen cap.
"""

import heapq
import json
from collections import defaultdict
from math import atan, degrees

import haversine as hs
import numpy as np
import shapely

SPACING_FEET = 20  # matches polygon_interior_grid's/space_polygon_exterior_points_evenly's default sample spacing
SPACING_METERS = SPACING_FEET / 3.28084
NEIGHBOR_RADIUS_MULTIPLIER = 1.8  # 8-connects the grid + links boundary to interior
VERTICAL_BAND_FRACTION = 0.05  # perimeter points within this fraction of the vertical drop from the top/bottom are valid start/end candidates
START_SLOPE_DEGREES = 70  # loosest slope cap the least-wandering pass starts from
STEP_DEGREES = 1  # how far each tightening step lowers the slope cap
MAX_GROWTH_MULTIPLIER = 1.2  # max route-length growth vs. loosest pass
SMOOTHING_WINDOW = 2  # points on each side averaged together in the smoothing pass

Point = tuple[float, float, float]  # (lon, lat, elevation)
# node index -> [(neighbor index, distance_m, slope_deg), ...]
Adjacency = dict[int, list[tuple[int, float, float]]]


def _bottleneck_dijkstra(adjacency: Adjacency, start: int, n_nodes: int) -> list[float]:
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


def _add_virtual_endpoints(
    adjacency: Adjacency,
    node_elev: np.ndarray,
    n_boundary: int,
    vertical_drop_fraction: float,
) -> tuple[int, int]:
    """
    Adds two virtual nodes to `adjacency` (indices len(node_elev) and
    len(node_elev) + 1): a virtual start with zero-cost edges to every
    boundary point within the top `vertical_drop_fraction` of the area's
    elevation range, and a virtual end with zero-cost edges FROM every
    boundary point within the bottom `vertical_drop_fraction`. This lets
    the route search treat any high/low-enough point on the perimeter as a
    valid start/end, rather than pinning to the single highest/lowest
    point. Mutates real boundary nodes' adjacency lists (for the end
    side).

    The vertical_drop_fraction threshold is based on the elevation range
    across *all* nodes (boundary + interior), so it's possible for no
    boundary point to qualify -- e.g. an interior knob taller than the
    entire rim. When that happens, falls back to just the single
    highest/lowest point on the perimeter, so there's always at least one
    valid start/end candidate.

    Returns (virtual_start_idx, virtual_end_idx).
    """
    n_nodes = len(node_elev)
    virtual_start_idx = n_nodes
    virtual_end_idx = n_nodes + 1

    vertical_drop = node_elev.max() - node_elev.min()
    top_threshold = node_elev.max() - vertical_drop_fraction * vertical_drop
    bottom_threshold = node_elev.min() + vertical_drop_fraction * vertical_drop

    start_candidates = [i for i in range(n_boundary) if node_elev[i] >= top_threshold]
    end_candidates = [i for i in range(n_boundary) if node_elev[i] <= bottom_threshold]

    if not start_candidates:
        start_candidates = [int(np.argmax(node_elev[:n_boundary]))]
    if not end_candidates:
        end_candidates = [int(np.argmin(node_elev[:n_boundary]))]

    for i in start_candidates:
        adjacency[virtual_start_idx].append((i, 0.0, 0.0))
    for i in end_candidates:
        adjacency[i].append((virtual_end_idx, 0.0, 0.0))

    return virtual_start_idx, virtual_end_idx


def _least_wandering_path(
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


def _find_best_max_slope(
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
        route_indices, route_length_m = _least_wandering_path(
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


def _smooth_route(
    nodes: list[Point], route_indices: list[int], window: int
) -> list[Point]:
    """
    Basic moving-average smoothing: replaces each interior route point with
    the average lon/lat/elevation of itself and its `window` neighbors on
    each side, to reduce the zig-zag from shortest-path tie-breaking on a
    lattice-like graph. Endpoints are left untouched so the route still
    starts/ends exactly at the top/bottom.
    """
    points = [nodes[i] for i in route_indices]
    n = len(points)
    smoothed = [points[0]]

    for i in range(1, n - 1):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        neighborhood = points[lo:hi]
        avg_lon = sum(p[0] for p in neighborhood) / len(neighborhood)
        avg_lat = sum(p[1] for p in neighborhood) / len(neighborhood)
        avg_elev = sum(p[2] for p in neighborhood) / len(neighborhood)
        smoothed.append((avg_lon, avg_lat, avg_elev))

    smoothed.append(points[-1])
    return smoothed


def get_area_route(
    geometry: dict[str, str],
    interior_geometry: dict[str, str],
    vertical_band_fraction: float = VERTICAL_BAND_FRACTION,
    neighbor_radius_multiplier: float = NEIGHBOR_RADIUS_MULTIPLIER,
    start_slope: float = START_SLOPE_DEGREES,
    step: float = STEP_DEGREES,
    max_growth_multiplier: float = MAX_GROWTH_MULTIPLIER,
    smoothing_window: int = SMOOTHING_WINDOW,
) -> dict[str, str]:
    """
    Accepts an area trail's boundary geometry (a Polygon geojson blob, as
    produced by space_polygon_exterior_points_evenly) and interior
    geometry (a MultiPoint geojson blob, as produced by
    polygon_interior_grid), both already elevation-populated, and returns
    a geojson LineString blob for the least-steep, least-wandering route
    from a high point on the perimeter to a low point. See the module
    docstring for the three-phase algorithm.

    Raises if no valid route can be found (e.g. the sampled points don't
    form a connected graph).
    """
    boundary_points = geometry["coordinates"][0]
    interior_points = interior_geometry["coordinates"]
    n_boundary = len(boundary_points)

    raw_nodes = list(boundary_points) + list(interior_points)
    # drop any point elevation lookups failed for
    nodes = [(p[0], p[1], p[2]) for p in raw_nodes if p[2] is not None]

    node_lon = np.array([p[0] for p in nodes])
    node_lat = np.array([p[1] for p in nodes])
    node_elev = np.array([p[2] for p in nodes])
    n_nodes = len(nodes)

    neighbor_radius_m = SPACING_METERS * neighbor_radius_multiplier
    meters_per_deg_lat = 111_320
    meters_per_deg_lon = 111_320 * np.cos(np.radians(node_lat.mean()))
    lon_window = neighbor_radius_m / meters_per_deg_lon
    lat_window = neighbor_radius_m / meters_per_deg_lat

    adjacency: Adjacency = defaultdict(list)

    for i in range(n_nodes):
        candidates = np.where(
            (np.abs(node_lon - node_lon[i]) <= lon_window)
            & (np.abs(node_lat - node_lat[i]) <= lat_window)
        )[0]
        for j in candidates:
            if j <= i:
                continue
            dist = hs.haversine(
                (node_lat[i], node_lon[i]),
                (node_lat[j], node_lon[j]),
                unit=hs.Unit.METERS,
            )
            if dist == 0 or dist > neighbor_radius_m:
                continue
            rise = node_elev[j] - node_elev[i]
            slope = abs(degrees(atan(rise / dist)))
            adjacency[i].append((j, dist, slope))
            adjacency[j].append((i, dist, slope))

    virtual_start_idx, virtual_end_idx = _add_virtual_endpoints(
        adjacency, node_elev, n_boundary, vertical_band_fraction
    )
    n_nodes_with_virtual = n_nodes + 2

    bottleneck = _bottleneck_dijkstra(
        adjacency, virtual_start_idx, n_nodes_with_virtual
    )
    slope_limit = bottleneck[virtual_end_idx]

    best = _find_best_max_slope(
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
            f"the loosest slope cap ({start_slope} degrees) -- the sampled points "
            "may not form a connected graph."
        )
    _max_slope, route_indices, _route_length_m = best

    route_indices = route_indices[1:-1]  # drop the virtual start/end bridging nodes
    route_points = _smooth_route(nodes, route_indices, window=smoothing_window)

    return json.loads(shapely.to_geojson(shapely.LineString(route_points)))
