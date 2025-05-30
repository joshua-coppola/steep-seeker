from core.osm.osm_processor import OSMProcessor


def test_OSMProcessor():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17


def test_identify_trails():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    trails = osm_processor.identify_trails()

    assert len(trails) == 188

    trail_info = {
        "id": [],
        "nodes": [],
        "name": [],
        "official_rating": [],
        "gladed": [],
        "area": [],
        "ungroomed": [],
        "park": [],
    }
    for trail in trails:
        assert "INVALID" not in trail["name"]
        for key in trail.keys():
            trail_info[key].append(trail[key])

    assert len(set(trail_info["name"])) == 120

    node_lengths = [len(nodes) for nodes in trail_info["nodes"]]
    assert sum(node_lengths) == 2224

    assert len(set(trail_info["official_rating"])) == 5
    assert sum(trail_info["gladed"]) == 17
    assert sum(trail_info["area"]) == 8
    assert sum(trail_info["ungroomed"]) == 13
    assert sum(trail_info["park"]) == 3


def test_identify_lifts():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    lifts = osm_processor.identify_lifts()

    assert len(lifts) == 20

    lift_info = {
        "id": [],
        "nodes": [],
        "name": [],
        "type": [],
        "occupancy": [],
        "capacity": [],
        "detatchable": [],
        "bubble": [],
        "heating": [],
    }
    for lift in lifts:
        assert "INVALID" not in lift["name"]
        for key in lift.keys():
            lift_info[key].append(lift[key])

    assert len(set(lift_info["name"])) == 20

    node_lengths = [len(nodes) for nodes in lift_info["nodes"]]
    assert sum(node_lengths) == 227

    assert len(set(lift_info["type"])) == 3

    occupancy_nums = [
        occupancy if occupancy else 0 for occupancy in lift_info["occupancy"]
    ]
    assert sum(occupancy_nums) == 54

    capacity_nums = [capacity if capacity else 0 for capacity in lift_info["capacity"]]
    assert sum(capacity_nums) == 650

    assert sum(lift_info["detatchable"]) == 5
    assert sum(lift_info["bubble"]) == 2
    assert sum(lift_info["heating"]) == 1
