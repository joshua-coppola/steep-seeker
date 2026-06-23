import shapely

from core.support.utils import space_line_points_evenly, polygon_interior_grid, get_length


def test_space_line_points_evenly():
    test_line = shapely.LineString([[0, 0], [0.001, 0.001]])

    output_line = space_line_points_evenly(test_line)

    assert len(shapely.to_geojson(output_line)) == 1335


def test_polygon_interior_grid():
    test_polygon = shapely.Polygon([[0, 0], [0, 0.01], [0.02, 0.02], [0.01, 0]])

    output_points = polygon_interior_grid(test_polygon, spacing_feet=100)

    assert len(output_points.geoms) == 2651


def test_get_length(trail):
    assert round(get_length(trail)) == 157250
