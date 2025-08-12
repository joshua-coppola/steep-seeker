import shapely

from core.support.utils import space_line_points_evenly


def test_space_line_points_evenly():
    test_line = shapely.LineString([[0, 0], [0.001, 0.001]])

    output_line = space_line_points_evenly(test_line)

    assert len(shapely.to_geojson(output_line)) == 1335
