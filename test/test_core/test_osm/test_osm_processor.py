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

    assert len(osm_processor.trails) == 151
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20
    assert osm_processor.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")


def test_get_trails(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)

    osm_processor_instance = osm_processor.OSMProcessor(osm_file)

    trails = osm_processor_instance.get_trails()

    assert len(trails) == 151
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
    assert trails["w10"].steepest_100ft == 9.9
    # w10 is ~34m (~112ft) long: shorter than pitch_window_feet (150ft), so
    # steepest_150ft also falls back to the whole-trail slope; 300ft doesn't
    assert trails["w10"].steepest_150ft == 9.9
    assert trails["w10"].steepest_300ft is None

    assert round(trails["w11"].length, 3) == 105.677
    # FakeElevation descends 1 unit per point, so w11 (19 points) drops 18
    assert trails["w11"].vertical == 18.0
    assert round(trails["w11"].max_slope, 3) == 27.127
    assert round(trails["w11"].average_slope, 3) == 10.298
    # w11 is ~106m (~347ft) long: 100/150/300ft windows exist, longer
    # windows don't fit so they fall back to None
    assert trails["w11"].steepest_100ft == 9.3
    assert trails["w11"].steepest_150ft == 9.3
    assert trails["w11"].steepest_300ft == 9.3
    assert trails["w11"].steepest_500ft is None
    assert trails["w11"].steepest_1320ft is None
    assert trails["w11"].steepest_2640ft is None
    assert trails["w11"].steepest_5280ft is None

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


def test_OSMProcessor_hikes_attributes(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    # the fixture has no piste:type=hike ways, so wiring hikes into
    # self.lifts should be a no-op
    assert osm_processor_instance.hikes == {}
    assert osm_processor_instance.hike_relations == {}
    assert len(osm_processor_instance.lifts) == 20


def test_OSMProcessor_merges_hikes_into_lifts(osm_file, monkeypatch):
    def fake_identify_hikes(ways, relations):
        return {
            "hikes": {
                "h1": {
                    "id": "h1",
                    "nodes": [1, 2],
                    "name": "Summit Bootpack",
                    "lift_type": "hike",
                    "occupancy": None,
                    "capacity": None,
                    "detachable": None,
                    "bubble": None,
                    "heating": None,
                }
            },
            "relations": {},
        }

    monkeypatch.setattr(osm_processor, "identify_hikes", fake_identify_hikes)

    osm_processor_instance = OSMProcessor(osm_file)

    assert osm_processor_instance.lifts["h1"]["lift_type"] == "hike"
    # real lifts parsed from the fixture are untouched
    assert len(osm_processor_instance.lifts) == 21


def test_flatten_relations_merges_when_match_fields_agree(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Bootpack"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": "Bootpack"},
    }
    relations = {"r1": {"id": "r1", "members": ["a1", "a2"], "type": "route"}}

    items, relations = osm_processor_instance._flatten_relations(
        items, relations, ["name"]
    )

    assert relations == {}
    assert list(items.keys()) == ["a1"]
    assert items["a1"]["nodes"] == [1, 2, 3]


def test_flatten_relations_skips_when_match_field_differs(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Bootpack"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": "Different Name"},
    }
    relations = {"r1": {"id": "r1", "members": ["a1", "a2"], "type": "route"}}

    items, relations = osm_processor_instance._flatten_relations(
        items, relations, ["name"]
    )

    assert "r1" in relations
    assert set(items.keys()) == {"a1", "a2"}


def test_merge_line_features_merges_adjacent_matching_items(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Bootpack"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": "Bootpack"},
    }

    merged = osm_processor_instance._merge_line_features(items, ["name"])

    assert len(merged) == 1
    (merged_item,) = merged.values()
    assert merged_item["nodes"] == [1, 2, 3]


def test_merge_line_features_is_unaware_of_lift_semantics(osm_file):
    # The merge pass only knows about match_fields/nodes -- it has no idea
    # occupancy/capacity/etc are lift-only fields. Two "real lifts" with
    # identical metadata sharing a station node would merge exactly like
    # this if the pass were ever run over the combined self.lifts dict,
    # which is why OSMProcessor keeps it scoped to self.hikes alone.
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "l1": {"id": "l1", "nodes": [1, 2], "lift_type": "chair_lift"},
        "l2": {"id": "l2", "nodes": [2, 3], "lift_type": "chair_lift"},
    }

    merged = osm_processor_instance._merge_line_features(items, ["lift_type"])

    assert len(merged) == 1


def test_get_center(osm_file):
    osm_processor = OSMProcessor(osm_file)

    actual_center = Point(-72.73652460768172, 43.41027958070422)

    assert osm_processor.get_center() == actual_center


def test_get_state(osm_file):
    osm_processor = OSMProcessor(osm_file)

    state = osm_processor.get_state()

    assert state == State("VT")


def test_get_direction(osm_file):
    osm_processor = OSMProcessor(osm_file)

    direction = osm_processor.get_direction()

    assert direction == "w"
