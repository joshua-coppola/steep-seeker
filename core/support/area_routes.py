"""
Finds the least-steep, least-wandering ski route down an area trail (a
glade, bowl, or other trail sampled as a polygon rather than a line).
This is designed to approximate the route an actual skier might take
inside the area.

Runs in three phases over a graph built from the area's sampled points
(the boundary ring plus the interior grid, per `polygon_interior_grid`):

1+2. Bottleneck + least-wandering passes -- see core.support.route_search
   for the shared algorithm (also used by multi_route.py for a branching
   trail's real graph).
3. Smoothing pass: a basic moving average over the route's lon/lat/
   elevation to reduce the zig-zag that shortest-path tie-breaking leaves
   behind on a lattice-like graph. Endpoints are left untouched. This
   step is area-specific -- multi_route.py skips it, since its graph is
   built from real mapped trail nodes rather than a synthetic sampled
   grid, so there's no zig-zag artifact to smooth away.
"""

import json
from collections import defaultdict
from math import atan, degrees

import haversine as hs
import numpy as np
import shapely

from core.support.route_search import (
    MAX_GROWTH_MULTIPLIER,
    START_SLOPE_DEGREES,
    STEP_DEGREES,
    VERTICAL_BAND_FRACTION,
    Adjacency,
    Point,
    add_virtual_endpoints,
    bottleneck_dijkstra,
    find_best_max_slope,
)

SPACING_FEET = 20  # matches polygon_interior_grid's/space_polygon_exterior_points_evenly's default sample spacing
SPACING_METERS = SPACING_FEET / 3.28084
NEIGHBOR_RADIUS_MULTIPLIER = 1.8  # 8-connects the grid + links boundary to interior
SMOOTHING_WINDOW = 2  # points on each side averaged together in the smoothing pass


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

    virtual_start_idx, virtual_end_idx = add_virtual_endpoints(
        adjacency,
        node_elev,
        range(n_boundary),
        range(n_boundary),
        vertical_band_fraction,
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
            f"the loosest slope cap ({start_slope} degrees) -- the sampled points "
            "may not form a connected graph."
        )
    _max_slope, route_indices, _route_length_m = best

    route_indices = route_indices[1:-1]  # drop the virtual start/end bridging nodes
    route_points = _smooth_route(nodes, route_indices, window=smoothing_window)

    return json.loads(shapely.to_geojson(shapely.LineString(route_points)))
