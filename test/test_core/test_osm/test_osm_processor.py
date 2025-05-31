from core.osm.osm_processor import OSMProcessor


def test_OSMProcessor():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    assert len(osm_processor.trails) == 179
    assert len(osm_processor.trail_relations) == 7

    assert len(osm_processor.lifts) == 20
