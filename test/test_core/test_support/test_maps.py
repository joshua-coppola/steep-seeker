import pytest
from shapely import LineString, Point, Polygon

from core.datamodels.state import State
from core.support.maps import (
    _find_map_size,
    _get_label_placement,
    _trail_color,
    create_map,
    create_thumbnail,
)
from core.support.mountain import Mountain
from core.support.trail import Trail


@pytest.fixture
def area_trail_mountain():
    """
    A standalone mountain with a single area trail: a unit square boundary
    (lon/lat 0-1) and a route running corner-to-corner across it.
    """
    trail = Trail(
        trail_id="w3000",
        mountain_id=1,
        geometry=Polygon(
            [[0, 0, 100], [0, 1, 100], [1, 1, 50], [1, 0, 50], [0, 0, 100]]
        ),
        interior_geometry=LineString([[0.4, 0.4, 80], [0.6, 0.6, 70]]),
        route=LineString([[0, 1, 100], [0.5, 0.5, 75], [1, 0, 50]]),
        name="Area Trail",
        official_rating="Expert",
        gladed=True,
        area=True,
        ungroomed=False,
        park=False,
        length=200,
        vertical=4,
        difficulty=40.0,
        max_slope=40.0,
        average_slope=20.0,
        steepest_30m=40.0,
    )

    return Mountain(
        mountain_id=1,
        name="Test Area Mountain",
        state=State.VERMONT,
        direction="e",
        coordinates=Point(0.5, 0.5),
        season_passes=[],
        trails={trail.trail_id: trail},
        lifts={},
    )


class TestTrailColor:
    def test_green_below_18(self):
        assert _trail_color(10) == "green"

    def test_blue_between_18_and_27(self):
        assert _trail_color(20) == "royalblue"

    def test_black_between_27_and_36(self):
        assert _trail_color(30) == "black"

    def test_red_between_36_and_47(self):
        assert _trail_color(40) == "red"

    def test_gold_above_47(self):
        assert _trail_color(50) == "gold"


class TestGetLabelPlacement:
    def test_zero_length_returns_zeroed_tuple(self):
        assert _get_label_placement([0, 1], [0, 1], 0, 5) == (0, 0, 0)

    def test_label_longer_than_available_run_returns_zeroed_tuple(self):
        # name_length=50 makes the label far longer than the 3-point trail,
        # so the +/- half-label-length window around the only "valid"
        # candidate point falls outside the point list entirely.
        assert _get_label_placement([0, 1, 2], [0, 0, 0], 10, 50) == (0, 0, 0)

    def test_flat_trail_places_label_at_midpoint_with_zero_angle(self):
        x = list(range(20))
        y = [0] * 20
        point, angle, label_length = _get_label_placement(x, y, 400, 3)

        assert (point, angle, label_length) == (10, pytest.approx(0.0), 66.0)


class TestFindMapSize:
    def test_bounds_include_trail_and_lift_points(self, mountain):
        dimensions = _find_map_size(mountain)

        assert dimensions == {
            "x_length": pytest.approx(111.17814425440771),
            "y_length": pytest.approx(111.1950802335329),
            "x_point": 1,
            "y_point": 1,
        }

    def test_bounds_for_area_trail_match_its_boundary(self, area_trail_mountain):
        dimensions = _find_map_size(area_trail_mountain)

        assert dimensions == {
            "x_length": pytest.approx(111.1950802335329),
            "y_length": pytest.approx(111.17814425440771),
            "x_point": 1.0,
            "y_point": 1.0,
        }


class TestCreateMap:
    def test_create_map_writes_svg(self, mountain, tmp_path):
        create_map(mountain, output_dir=str(tmp_path))

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert output_file.exists()
        assert output_file.read_text().startswith("<?xml")

    def test_create_map_without_labels(self, mountain, tmp_path):
        create_map(mountain, output_dir=str(tmp_path), with_labels=False)

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert output_file.exists()

    def test_create_map_debug_mode_with_area_trail(self, area_trail_mountain, tmp_path):
        create_map(area_trail_mountain, output_dir=str(tmp_path), debug_mode=True)

        output_file = (
            tmp_path
            / area_trail_mountain.state.value
            / f"{area_trail_mountain.name}.svg"
        )
        assert output_file.exists()


class TestCreateThumbnail:
    def test_create_thumbnail_writes_svg(self, mountain, tmp_path):
        create_thumbnail(mountain, output_dir=str(tmp_path))

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert output_file.exists()
        assert output_file.read_text().startswith("<?xml")
