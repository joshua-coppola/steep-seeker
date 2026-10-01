from itertools import pairwise
from math import atan, degrees

import haversine as hs
import numpy as np
import pytest

from core.support.area_routes import get_area_route


def _sloped_square(
    lat0=40.600,
    lon0=-111.600,
    side_m=200,
    n_interior=34,
    top_elev=100.0,
    bottom_elev=40.0,
):
    """
    Builds a geojson boundary/interior geometry pair for a `side_m` x
    `side_m` square area, sloping evenly from `top_elev` at the north edge
    to `bottom_elev` at the south edge, sampled at a realistic ~6m interior
    grid spacing (n_interior^2 points across side_m meters).
    """
    lat_span = side_m / 111_320
    lon_span = side_m / (111_320 * np.cos(np.radians(lat0)))

    def elev_at(lat):
        frac = (lat0 - lat) / lat_span
        return top_elev - frac * (top_elev - bottom_elev)

    boundary = [
        [lon0, lat0, elev_at(lat0)],
        [lon0 + lon_span, lat0, elev_at(lat0)],
        [lon0 + lon_span, lat0 - lat_span, elev_at(lat0 - lat_span)],
        [lon0, lat0 - lat_span, elev_at(lat0 - lat_span)],
        [lon0, lat0, elev_at(lat0)],
    ]
    geometry = {"type": "Polygon", "coordinates": [boundary]}

    interior = []
    for lon in np.linspace(lon0, lon0 + lon_span, n_interior):
        for lat in np.linspace(lat0 - lat_span, lat0, n_interior):
            interior.append([lon, lat, elev_at(lat)])
    interior_geometry = {"type": "MultiPoint", "coordinates": interior}

    return geometry, interior_geometry


def test_get_area_route_matches_expected_route():
    geometry, interior_geometry = _sloped_square()

    route = get_area_route(geometry, interior_geometry)

    assert route["type"] == "LineString"
    coordinates = route["coordinates"]

    # symmetric square sloping only by latitude -> the least-steep route is
    # a straight line straight down the fall line
    assert len(coordinates) == 34
    assert coordinates[0] == pytest.approx([-111.597634, 40.6, 100.0], abs=1e-6)
    assert coordinates[-1] == pytest.approx([-111.597634, 40.598203, 40.0], abs=1e-6)

    total_length_m = sum(_haversine(a, b) for a, b in pairwise(coordinates))
    assert round(total_length_m, 2) == 199.78


def test_get_area_route_steepest_segment_matches_expected_value():
    geometry, interior_geometry = _sloped_square()

    route = get_area_route(geometry, interior_geometry)
    coordinates = route["coordinates"]

    steepest = max(_slope_degrees(a, b) for a, b in pairwise(coordinates))

    assert round(steepest, 2) == 16.72


def test_get_area_route_falls_back_when_no_boundary_point_qualifies():
    # An interior point far taller than the entire rim: no boundary point
    # falls within the default 5% vertical-drop band from the top, so
    # add_virtual_endpoints must fall back to the single highest boundary
    # point (the NW corner, (lon0, lat0)) rather than leaving the start
    # candidates empty.
    geometry, interior_geometry = _sloped_square()
    lon_mid = (geometry["coordinates"][0][0][0] + geometry["coordinates"][0][1][0]) / 2
    lat_mid = (geometry["coordinates"][0][0][1] + geometry["coordinates"][0][2][1]) / 2
    interior_geometry["coordinates"].append([lon_mid, lat_mid, 500.0])

    route = get_area_route(geometry, interior_geometry)
    coordinates = route["coordinates"]

    assert coordinates[0] == pytest.approx([-111.6, 40.6, 100.0], abs=1e-6)
    assert coordinates[-1] == pytest.approx([-111.6, 40.598203, 40.0], abs=1e-6)


def _haversine(point_a, point_b):
    lon_a, lat_a, _ = point_a
    lon_b, lat_b, _ = point_b
    return hs.haversine((lat_a, lon_a), (lat_b, lon_b), unit=hs.Unit.METERS)


def _slope_degrees(point_a, point_b):
    dist = _haversine(point_a, point_b)
    return abs(degrees(atan((point_a[2] - point_b[2]) / dist)))
