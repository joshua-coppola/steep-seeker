from core.osm.osm_processor import OSMProcessor
from core.osm.trail_parser import identify_trails, identify_lifts


def test_identify_trails():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    trails = identify_trails(osm_processor.ways, osm_processor.relations)

    assert len(trails["trails"]) == 188
    assert len(trails["relations"]) == 7

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
    for trail in trails["trails"].values():
        assert "INVALID" not in trail["name"]
        for key in trail.keys():
            trail_info[key].append(trail[key])

    assert len(set(trail_info["name"])) == 128

    node_lengths = [len(nodes) for nodes in trail_info["nodes"]]
    assert sum(node_lengths) == 2251

    assert len(set(trail_info["official_rating"])) == 5
    assert sum(trail_info["gladed"]) == 17
    assert sum(trail_info["area"]) == 8
    assert sum(trail_info["ungroomed"]) == 13
    assert sum(trail_info["park"]) == 3


def test_identify_lifts():
    osm_processor = OSMProcessor("test/test_core/test_osm/test.osm")

    lifts = identify_lifts(osm_processor.ways)

    assert len(lifts["lifts"]) == 20

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
    for lift in lifts["lifts"].values():
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
