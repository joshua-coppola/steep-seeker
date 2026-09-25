import math
import re

import matplotlib.pyplot as plt
import pytest
from shapely import LineString, Point, Polygon

from core.datamodels.state import State
from core.support.maps import (
    MAP_SIMPLIFY_TOLERANCE,
    _find_map_size,
    _get_label_placement,
    _populate_map,
    _save_map_svg,
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
        mountain_id="1",
        geometry=Polygon(
            [[0, 0, 100], [0, 1, 100], [1, 1, 50], [1, 0, 50], [0, 0, 100]]
        ),
        interior_geometry=LineString([[0.4, 0.4, 80], [0.6, 0.6, 70]]),
        route=LineString([[0, 1, 100], [0.5, 0.5, 75], [1, 0, 50]]),
        name="Area Trail",
        official_rating="Expert",
        gladed=True,
        area=True,
        multi_route=False,
        ungroomed=False,
        park=False,
        hazardous=False,
        length=200,
        vertical=4,
        difficulty=40.0,
        max_slope=40.0,
        average_slope=20.0,
        steepest_100ft=40.0,
        steepest_150ft=40.0,
    )

    return Mountain(
        mountain_id="1",
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
        assert _trail_color(60) == "gold"


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
    def test_bounds_include_trail_and_lift_points(self, mountain_factory):
        mountain = mountain_factory()
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
    def test_create_map_writes_svg(self, mountain_factory, tmp_path):
        mountain = mountain_factory()
        create_map(mountain, output_dir=str(tmp_path))

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert output_file.exists()
        assert output_file.read_text().startswith("<?xml")

    def test_create_map_without_labels(self, mountain_factory, tmp_path):
        mountain = mountain_factory()
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

    def test_create_map_draws_hike_lift_dotted(
        self, mountain_factory, trail_factory, lift_factory, tmp_path
    ):
        # gladed=False so the only source of a dasharray in this map is the
        # hike lift, isolating it from the gladed=dashed styling tested
        # elsewhere
        mountain = mountain_factory(
            trails={"w1000": trail_factory(gladed=False)},
            lifts={"w1001": lift_factory(lift_id="w1001", lift_type="hike")},
        )
        create_map(mountain, output_dir=str(tmp_path))

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert "stroke-dasharray" in output_file.read_text()

    def test_create_map_simplifies_dense_geometry(
        self, mountain_factory, trail_factory, tmp_path
    ):
        # a straight line with many redundant collinear points -- simplify()
        # collapses these to just the two endpoints regardless of tolerance,
        # while no tolerance draws every one of them. create_map wires up
        # MAP_SIMPLIFY_TOLERANCE, a much smaller value than
        # create_thumbnail's (this map is zoomable up to 100x), but it
        # should still measurably thin geometry this dense.
        dense_points = [[0, i * 0.001, 100] for i in range(200)]
        mountain = mountain_factory(
            trails={
                "w1": trail_factory(trail_id="w1", geometry=LineString(dense_points))
            }
        )

        plt.subplots()
        _populate_map(
            mountain, with_labels=False, simplify_tolerance=MAP_SIMPLIFY_TOLERANCE
        )
        _save_map_svg(mountain, str(tmp_path / "simplified"))

        plt.subplots()
        _populate_map(mountain, with_labels=False, simplify_tolerance=None)
        _save_map_svg(mountain, str(tmp_path / "unsimplified"))

        simplified_svg = (
            tmp_path / "simplified" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()
        unsimplified_svg = (
            tmp_path / "unsimplified" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()

        assert len(simplified_svg) < len(unsimplified_svg)

    def test_create_map_label_rotation_unaffected_by_simplification(
        self, mountain_factory, trail_factory, tmp_path
    ):
        # a curved arc, not a straight line -- a straight line's label
        # angle looks the same whether it's built from 2 points or 100,
        # so it wouldn't have caught the regression where simplified
        # (far fewer, differently-spaced) points fed into
        # _get_label_placement threw off the computed rotation angle
        arc_points = [
            [0.01 * math.cos(t), 0.01 * math.sin(t), 100]
            for t in (i * (math.pi / 2) / 99 for i in range(100))
        ]
        mountain = mountain_factory(
            trails={"w1": trail_factory(trail_id="w1", geometry=LineString(arc_points))}
        )

        plt.subplots()
        _populate_map(mountain, with_labels=True, simplify_tolerance=None)
        _save_map_svg(mountain, str(tmp_path / "unsimplified"))

        plt.subplots()
        _populate_map(
            mountain, with_labels=True, simplify_tolerance=MAP_SIMPLIFY_TOLERANCE
        )
        _save_map_svg(mountain, str(tmp_path / "simplified"))

        unsimplified_svg = (
            tmp_path / "unsimplified" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()
        simplified_svg = (
            tmp_path / "simplified" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()

        # label position/rotation must come from the full-precision curve
        # regardless of what the drawn line itself was simplified to
        assert re.findall(r"rotate\(([-\d.]+)", unsimplified_svg) == re.findall(
            r"rotate\(([-\d.]+)", simplified_svg
        )


class TestCreateThumbnail:
    def test_create_thumbnail_writes_svg(self, mountain_factory, tmp_path):
        mountain = mountain_factory()
        create_thumbnail(mountain, output_dir=str(tmp_path))

        output_file = tmp_path / mountain.state.value / f"{mountain.name}.svg"
        assert output_file.exists()
        assert output_file.read_text().startswith("<?xml")

    def test_create_thumbnail_simplifies_dense_geometry(
        self, mountain_factory, trail_factory, tmp_path
    ):
        # a straight line with many redundant collinear points -- simplify()
        # collapses these to just the two endpoints regardless of tolerance,
        # while create_map (no simplification) draws every one of them, so
        # a big size gap here isolates the simplification effect from the
        # (also real, but separate) labels-off savings
        dense_points = [[0, i * 0.001, 100] for i in range(200)]
        mountain = mountain_factory(
            trails={
                "w1": trail_factory(trail_id="w1", geometry=LineString(dense_points))
            }
        )

        create_map(mountain, output_dir=str(tmp_path / "map"), with_labels=False)
        create_thumbnail(mountain, output_dir=str(tmp_path / "thumb"))

        map_svg = (
            tmp_path / "map" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()
        thumb_svg = (
            tmp_path / "thumb" / mountain.state.value / f"{mountain.name}.svg"
        ).read_text()

        assert len(thumb_svg) < len(map_svg) / 2
