from core.osm.osm_processor import OSMProcessor


def test_OSMProcessor():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    assert len(osm_processor.trails) == 159
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20


def test_get_trails():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    trails = osm_processor.get_trails()

    assert len(trails) == 159
    assert len(str(trails["w10"]["geometry"])) == 98


def test_get_lifts():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    lifts = osm_processor.get_lifts()

    assert len(lifts) == 20
    assert len(str(lifts["w113"]["geometry"])) == 55
