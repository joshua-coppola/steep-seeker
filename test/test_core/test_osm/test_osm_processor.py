from uuid import UUID
from shapely import Point

from core.osm import osm_processor
from core.osm.osm_processor import OSMProcessor
from core.datamodels.state import State

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
    assert len(trails["w11"].geometry["coordinates"]) == 19
    # Area Example
    assert len(trails["w10"].geometry["coordinates"][0]) == 36

    assert round(trails["w11"].length, 3) == 105.677
    # FakeElevation returns 1500.0 for every point, so slope is flat
    assert trails["w11"].max_slope == 0
    assert trails["w11"].average_slope == 0

    for trail_id, trail in trails.items():
        coords = trail.geometry["coordinates"]

        # Handle both LineString and Polygon coordinate structures
        if trail.area:
            # For polygons, coordinates are nested one level deeper
            assert isinstance(coords, list)
            assert len(coords) > 0
            actual_coords = coords[0] if coords else []
        else:
            # For lines, coordinates are flat
            actual_coords = coords

        # Now check that coordinates have elevation
        assert all(len(coord) == 3 for coord in actual_coords), (
            f"Trail {trail_id}: Not all coords have 3 values. Sample: {actual_coords[:3]}"
        )
        assert all(coord[2] == 1500.0 for coord in actual_coords), (
            f"Trail {trail_id}: Not all elevations are 1500. Sample: {actual_coords[:3]}"
        )


def test_get_lifts(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)

    osm_processor_instance = osm_processor.OSMProcessor(osm_file)

    lifts = osm_processor_instance.get_lifts()

    assert len(lifts) == 20
    assert len(lifts["w113"].geometry["coordinates"]) == 124
    assert len(lifts["w113"].geometry["coordinates"][0]) == 3

    # FakeElevation returns 1500.0 for every point, so drop/slope is 0
    assert lifts["w113"].vertical == 0
    assert lifts["w113"].average_slope == 0


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
