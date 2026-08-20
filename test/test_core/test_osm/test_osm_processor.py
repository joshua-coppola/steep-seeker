from uuid import UUID

from shapely import LineString, Point

from core.datamodels.state import State
from core.osm import osm_processor
from core.osm.osm_processor import OSMProcessor
from test.test_core.conftest import FakeElevation


def test_OSMProcessor(osm_file):
    osm_processor = OSMProcessor(osm_file)

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    assert len(osm_processor.trails) == 159
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20
    assert osm_processor.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")


def test_get_trails(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)

    osm_processor_instance = osm_processor.OSMProcessor(osm_file)

    trails = osm_processor_instance.get_trails()

    assert len(trails) == 159
    assert isinstance(trails, dict)
    # Non Area Example
    assert len(list(trails["w11"].geometry.coords)) == 19
    # Area Example
    assert len(list(trails["w10"].geometry.exterior.coords)) == 36

    # route is only computed for area trails
    assert trails["w11"].route is None
    assert isinstance(trails["w10"].route, LineString)
    route_coords = list(trails["w10"].route.coords)
    # the route is re-spaced and re-queried for elevation after smoothing
    # (see get_trails), so its point count/spacing no longer matches the
    # boundary/interior grid's
    assert len(route_coords) == 7
    assert route_coords[0] == (-72.741146, 43.393933, 1500.0)

    # length/slope stats for an area trail are computed off its route
    # (a real line), not its boundary polygon (not a line to walk along)
    assert round(trails["w10"].length, 3) == 34.266
    assert trails["w10"].vertical == 34.0
    assert round(trails["w10"].max_slope, 3) == 11.655
    assert round(trails["w10"].average_slope, 3) == 10.018
    assert trails["w10"].steepest_30m == 9.9
    assert trails["w10"].steepest_50m is None
    assert trails["w10"].steepest_100m is None

    assert round(trails["w11"].length, 3) == 105.677
    # FakeElevation descends 1 unit per point, so w11 (19 points) drops 18
    assert trails["w11"].vertical == 18.0
    assert round(trails["w11"].max_slope, 3) == 27.127
    assert round(trails["w11"].average_slope, 3) == 10.298
    # w11 is ~106m long: 30/50/100m windows exist, longer windows don't fit
    # so they fall back to None
    assert trails["w11"].steepest_30m == 9.3
    assert trails["w11"].steepest_50m == 10.0
    assert trails["w11"].steepest_100m == 9.3
    assert trails["w11"].steepest_200m is None
    assert trails["w11"].steepest_500m is None
    assert trails["w11"].steepest_1000m is None

    for trail_id, trail in trails.items():
        # Polygons expose their ring via .exterior.coords; lines via .coords
        if trail.area:
            actual_coords = list(trail.geometry.exterior.coords)
            assert actual_coords[-1] == actual_coords[0], (
                f"Trail {trail_id}: ring isn't closed. "
                f"First: {actual_coords[0]}, last: {actual_coords[-1]}"
            )
        else:
            actual_coords = list(trail.geometry.coords)

        # Now check that coordinates have elevation
        assert all(len(coord) == 3 for coord in actual_coords), (
            f"Trail {trail_id}: Not all coords have 3 values. Sample: {actual_coords[:3]}"
        )

        # FakeElevation starts at 1500 and drops 1 per new (lon, lat) point
        # seen in the segment; a repeated coordinate (e.g. a closed ring's
        # start/end, or a resampling artifact) reuses the elevation it was
        # first assigned rather than continuing to descend
        seen = {}
        for coord in actual_coords:
            key = (coord[0], coord[1])
            if key not in seen:
                seen[key] = 1500.0 - len(seen)
            assert coord[2] == seen[key], (
                f"Trail {trail_id}: elevation mismatch at {coord}, expected {seen[key]}"
            )


def test_get_lifts(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)

    osm_processor_instance = osm_processor.OSMProcessor(osm_file)

    lifts = osm_processor_instance.get_lifts()

    assert len(lifts) == 20
    lift_coords = list(lifts["w113"].geometry.coords)
    assert len(lift_coords) == 124
    assert len(lift_coords[0]) == 3

    # FakeElevation descends 1 unit per point, so w113 (124 points) drops 123
    assert lifts["w113"].vertical == 123.0
    assert round(lifts["w113"].average_slope, 3) == 9.923


def test_get_center(osm_file):
    osm_processor = OSMProcessor(osm_file)

    actual_center = Point(-72.73644922151608, 43.4102903790286)

    assert osm_processor.get_center() == actual_center


def test_get_state(osm_file):
    osm_processor = OSMProcessor(osm_file)

    state = osm_processor.get_state()

    assert state == State("VT")


def test_get_direction(osm_file):
    osm_processor = OSMProcessor(osm_file)

    direction = osm_processor.get_direction()

    assert direction == "w"
