import shapely
from decimal import Decimal

from core.support.utils import (
    space_line_points_evenly,
    polygon_interior_grid,
    get_length,
    get_vertical_drop,
    get_max_slope,
    get_average_slope,
    get_steepest_pitch,
)


def test_space_line_points_evenly():
    test_line = shapely.LineString([[0, 0], [0.001, 0.001]])

    output_line = space_line_points_evenly(test_line)

    assert len(shapely.to_geojson(output_line)) == 1335


def test_polygon_interior_grid():
    test_polygon = shapely.Polygon([[0, 0], [0, 0.01], [0.02, 0.02], [0.01, 0]])

    output_points = polygon_interior_grid(test_polygon, spacing_feet=100)

    assert len(output_points.geoms) == 2651


def test_get_length():
    geojson = {
        'type': 'LineString', 
        'coordinates': [
            [Decimal('-72.718289'), Decimal('43.422299'), 1500.0],
            [Decimal('-72.718362'), Decimal('43.422312'), 1500.0],
        ],
    }

    assert round(get_length(geojson), 2) == 6.07


def test_get_vertical_drop_line():
    geometry = {"coordinates": [[-120.0, 40.0, 100], [-120.01, 40.01, 300], [-120.02, 40.02, 200]]}
    assert get_vertical_drop(geometry) == 200


def test_get_vertical_drop_nested_area():
    geometry = {"coordinates": [[[-120.0, 40.0, 50], [-120.01, 40.01, 150]] ]}
    assert get_vertical_drop(geometry) == 100


def test_get_vertical_drop_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_vertical_drop(geometry) is None


def test_get_max_slope():
    geometry = {"coordinates": [[-120.0, 40.0, 100], [-120.01, 40.01, 300], [-120.02, 40.02, 200]]}
    assert round(get_max_slope(geometry), 2) == 8.13


def test_get_max_slope_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_max_slope(geometry) is None


def test_get_average_slope():
    geometry = {"coordinates": [[-120.0, 40.0, 100], [-120.01, 40.01, 300], [-120.02, 40.02, 200]]}
    assert round(get_average_slope(geometry), 2) == 6.11


def test_get_average_slope_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_average_slope(geometry) is None


# A steady-grade line ~556m long, dropping 20m every ~55.6m (constant ~19.8 degree pitch)
STEADY_GRADE_LINE = {
    "coordinates": [
        [-120.0, 40.0 + i * 0.0005, 1000 - i * 20] for i in range(11)
    ]
}


def test_get_steepest_pitch_finds_window():
    assert get_steepest_pitch(STEADY_GRADE_LINE, 100) == 19.8


def test_get_steepest_pitch_no_window_long_returns_none():
    # trail is ~556m; no 1000m window exists and 1000 > 30, so no fallback
    assert get_steepest_pitch(STEADY_GRADE_LINE, 1000) is None


def test_get_steepest_pitch_short_trail_falls_back_to_overall_slope():
    # trail is ~14m, shorter than the 30m window, so falls back to the
    # whole-trail slope instead of returning None
    geometry = {"coordinates": [[-120.0, 40.0, 100], [-120.0001, 40.0001, 105]]}
    assert get_steepest_pitch(geometry, 30) == 19.6


def test_get_steepest_pitch_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_steepest_pitch(geometry, 30) is None


def test_get_steepest_pitch_too_few_points():
    geometry = {"coordinates": [[-120.0, 40.0, 100]]}
    assert get_steepest_pitch(geometry, 30) is None
