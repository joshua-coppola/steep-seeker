from core.osm.osm_reader import OSMHandler


def test_OSMHandler(osm_file):
    osm_handler = OSMHandler()
    osm_handler.apply_file(osm_file)

    assert len(osm_handler.nodes) == 17415
    assert len(osm_handler.ways) == 829
    assert len(osm_handler.relations) == 17
