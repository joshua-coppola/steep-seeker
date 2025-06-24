from uuid import UUID

from core.osm.osm_processor import OSMProcessor
from core.support.states import State


def test_OSMProcessor():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    assert len(osm_processor.trails) == 159
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20
    assert osm_processor.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")


def test_get_trails():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    trails = osm_processor.get_trails()

    assert len(trails) == 159
    assert len(trails["w10"].geometry) == 128


def test_get_lifts():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    lifts = osm_processor.get_lifts()

    assert len(lifts) == 20
    assert len(lifts["w113"].geometry) == 83


def test_get_state():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    state = osm_processor.get_state()

    assert state == State("VT")


def test_get_direction(osm_file):
    osm_processor = OSMProcessor(osm_file)

    direction = osm_processor.get_direction()

    assert direction == "w"
