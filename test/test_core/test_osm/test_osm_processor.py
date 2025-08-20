from uuid import UUID
from shapely import Point

from core.osm.osm_processor import OSMProcessor
from core.datamodels.state import State


def test_OSMProcessor(osm_file):
    osm_processor = OSMProcessor(osm_file)

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    assert len(osm_processor.trails) == 159
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20
    assert osm_processor.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")


def test_get_trails(osm_file):
    osm_processor = OSMProcessor(osm_file)

    trails = osm_processor.get_trails()

    assert len(trails) == 159
    assert len(trails["w10"].geometry) == 128


def test_get_lifts(osm_file):
    osm_processor = OSMProcessor(osm_file)

    lifts = osm_processor.get_lifts()

    assert len(lifts) == 20
    assert len(lifts["w113"].geometry) == 4877


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
