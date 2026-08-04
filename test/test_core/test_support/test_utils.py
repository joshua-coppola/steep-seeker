import shapely
from decimal import Decimal

from core.support.utils import (
    space_line_points_evenly,
    polygon_interior_grid,
    get_length,
    get_vertical_drop,
    get_max_slope,
    get_average_slope,
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
