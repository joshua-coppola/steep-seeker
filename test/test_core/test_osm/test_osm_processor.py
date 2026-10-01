from uuid import UUID

from shapely import LineString, Point

from core.datamodels.state import State
from core.osm import osm_processor
from core.osm.osm_processor import OSMProcessor
from test.test_core.conftest import FakeElevation


def _close_together_nodes(ids):
    """
    Fake node id -> {lon, lat} coordinates, spaced ~25ft apart per unit of
    id difference -- for _merge_multi_route_clusters tests that use small
    synthetic node ids (not present in the real osm_file fixture) and need
    _way_length_feet to see *some* short, well-under-threshold length.
    """
    return {node_id: {"lon": -72.8 + 0.0001 * node_id, "lat": 43.4} for node_id in ids}


def test_OSMProcessor(osm_file):
    osm_processor = OSMProcessor(osm_file)

    assert len(osm_processor.nodes) == 17415
    assert len(osm_processor.ways) == 829
    assert len(osm_processor.relations) == 17

    # 151 raw trail ways, 11 of which fold into 7 multi_route trails (a
    # branch/rejoin the endpoint-only merge in _merge_line_features can't
    # collapse into a single chain) -- see
    # test_merge_multi_route_clusters_* below and get_trails' multi_route
    # assertions for the real branching trails this fixture contains
    # ("Dream Weaver", "Rimrock", "Vortex", "Quantum Leap", "Sunset Strip",
    # "Green Link", plus one unnamed 10-branch cluster)
    assert len(osm_processor.trails) == 140
    assert len(osm_processor.trail_relations) == 1

    assert len(osm_processor.lifts) == 20
    assert osm_processor.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")


def test_get_trails(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)

    osm_processor_instance = osm_processor.OSMProcessor(osm_file)

    trails = osm_processor_instance.get_trails()

    assert len(trails) == 140
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

    # Multi-route example -- "Sunset Strip" is a real forking trail in this
    # fixture (see test_merge_multi_route_clusters_* for the merge logic in
    # isolation): its geometry keeps every branch (real, mapped lines, all
    # rendered), while its route (the rating basis) picks the least-steep
    # path through them
    multi_route_trail = trails["w257663060"]
    assert multi_route_trail.name == "Sunset Strip"
    assert multi_route_trail.multi_route is True
    assert multi_route_trail.geometry.geom_type == "MultiLineString"
    assert len(multi_route_trail.geometry.geoms) > 1
    assert multi_route_trail.route is not None
    assert multi_route_trail.max_slope is not None
    assert multi_route_trail.length > 0

    for trail_id, trail in trails.items():
        # Polygons expose their ring via .exterior.coords; lines via
        # .coords; a multi-route trail's MultiLineString has neither --
        # each branch's own .coords is concatenated in geometry order,
        # matching how _elevation_populated_branches queried them
        if trail.area:
            actual_coords = list(trail.geometry.exterior.coords)
            assert actual_coords[-1] == actual_coords[0], (
                f"Trail {trail_id}: ring isn't closed. "
                f"First: {actual_coords[0]}, last: {actual_coords[-1]}"
            )
        elif trail.multi_route:
            actual_coords = [
                coord for line in trail.geometry.geoms for coord in line.coords
            ]
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


def test_merge_multi_route_clusters_lone_trail_is_untouched(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {"a1": {"id": "a1", "nodes": [1, 2], "name": "Solo"}}

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert merged == items


def test_merge_multi_route_clusters_non_touching_same_name_stays_separate(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Twin Peaks"},
        "a2": {"id": "a2", "nodes": [3, 4], "name": "Twin Peaks"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert merged == items


def test_merge_multi_route_clusters_never_clusters_area_trails(osm_file):
    # an area trail's geometry is a Polygon boundary; a multi_route trail's
    # is a branches MultiLineString -- _build_trail_geometry can only
    # build one or the other, so two touching, same-named area ways must
    # never become one multi_route trail (that would leave "area" True
    # with a MultiLineString geometry, crashing anything that trusts area
    # to mean "this is a Polygon", e.g. maps.py/routes.py's ".exterior")
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2, 3], "name": "Glade", "area": True},
        "a2": {"id": "a2", "nodes": [3, 4, 1], "name": "Glade", "area": True},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name", "area"])

    assert merged == items


def test_merge_multi_route_clusters_differently_named_touching_ways_stay_separate(
    osm_file,
):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Alpha"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": "Beta"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert merged == items


def test_merge_multi_route_clusters_unnamed_bridge_does_not_fuse_two_named_trails(
    osm_file,
):
    # an unnamed connector between two *different* real named trails (e.g.
    # a crossing/junction piece) must not transitively merge them together
    # just because it's compatible with both individually
    osm_processor_instance = OSMProcessor(osm_file)
    osm_processor_instance.nodes = _close_together_nodes(range(1, 5))

    items = {
        "portal": {"id": "portal", "nodes": [1, 2], "name": "Portal"},
        "bridge": {"id": "bridge", "nodes": [2, 3], "name": ""},
        "klodinke": {"id": "klodinke", "nodes": [3, 4], "name": "Klodinke"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert len(merged) == 2
    portal = next(t for t in merged.values() if t.get("name") == "Portal")
    klodinke = next(t for t in merged.values() if t.get("name") == "Klodinke")
    assert portal["multi_route"] is True
    assert sorted(portal["branches"]) == [[1, 2], [2, 3]]
    # Klodinke never touched anything with a conflicting name, so it's
    # untouched -- still a lone item, not folded into Portal
    assert "multi_route" not in klodinke
    assert klodinke["nodes"] == [3, 4]


def test_merge_multi_route_clusters_named_trail_keeps_continuing_past_an_unnamed_crossing(
    osm_file,
):
    # a trail (Tombstone) that continues past an intersection via an
    # unnamed connector piece must keep merging with its own continuation,
    # even though that same unnamed piece also touches a different named
    # trail (Klodinke) at the crossing -- Tombstone shouldn't stop early
    # and Klodinke shouldn't get pulled in
    osm_processor_instance = OSMProcessor(osm_file)
    osm_processor_instance.nodes = _close_together_nodes(range(1, 6))

    items = {
        "tombstone_before": {
            "id": "tombstone_before",
            "nodes": [1, 2],
            "name": "Tombstone",
        },
        "crossing": {"id": "crossing", "nodes": [2, 3], "name": ""},
        "tombstone_after": {
            "id": "tombstone_after",
            "nodes": [3, 4],
            "name": "Tombstone",
        },
        "klodinke": {"id": "klodinke", "nodes": [3, 5], "name": "Klodinke"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert len(merged) == 2
    tombstone = next(t for t in merged.values() if t.get("name") == "Tombstone")
    klodinke = next(t for t in merged.values() if t.get("name") == "Klodinke")
    assert tombstone["multi_route"] is True
    assert sorted(tombstone["branches"]) == [[1, 2], [2, 3], [3, 4]]
    assert "multi_route" not in klodinke
    assert klodinke["nodes"] == [3, 5]


def test_merge_multi_route_clusters_fork_and_rejoin_becomes_one_trail(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        # trunk down to the fork at node 3
        "a1": {"id": "a1", "nodes": [1, 2, 3], "name": "Fork Run"},
        # two alternate lines from the fork (3) back to the rejoin (7)
        "a2": {"id": "a2", "nodes": [3, 4, 7], "name": "Fork Run"},
        "a3": {"id": "a3", "nodes": [3, 6, 7], "name": "Fork Run"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert len(merged) == 1
    (trail,) = merged.values()
    assert trail["multi_route"] is True
    assert trail["name"] == "Fork Run"
    assert "nodes" not in trail
    assert sorted(trail["branches"]) == [[1, 2, 3], [3, 4, 7], [3, 6, 7]]


def test_merge_multi_route_clusters_splits_at_an_interior_touch_point(osm_file):
    # a2 splits off midway through a1 (at node 3), not at either way's own
    # end -- the branch this creates out of a1 must still end up with its
    # own real endpoint at the touch point, so it's split there rather than
    # kept as one [1,2,3,4,5] branch
    osm_processor_instance = OSMProcessor(osm_file)

    items = {
        "a1": {"id": "a1", "nodes": [1, 2, 3, 4, 5], "name": "Spur Run"},
        "a2": {"id": "a2", "nodes": [3, 9], "name": "Spur Run"},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert len(merged) == 1
    (trail,) = merged.values()
    assert trail["multi_route"] is True
    assert sorted(trail["branches"]) == [[1, 2, 3], [3, 4, 5], [3, 9]]


def test_merge_multi_route_clusters_unnamed_way_merges_into_named_one(osm_file):
    osm_processor_instance = OSMProcessor(osm_file)
    osm_processor_instance.nodes = _close_together_nodes(range(1, 4))

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Real Name"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": ""},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert len(merged) == 1
    (trail,) = merged.values()
    assert trail["multi_route"] is True
    # the named member's name wins over the unnamed one's
    assert trail["name"] == "Real Name"


def test_merge_multi_route_clusters_long_unnamed_way_stays_separate(osm_file):
    # an unnamed way at or over MULTI_ROUTE_UNNAMED_MAX_LENGTH_FEET is more
    # likely a genuinely separate, merely nameless, trail than an actual
    # branch -- it should not get folded into a touching named trail
    osm_processor_instance = OSMProcessor(osm_file)
    osm_processor_instance.nodes = {
        1: {"lon": -72.8, "lat": 43.4},
        2: {"lon": -72.8, "lat": 43.4},
        # ~0.006 degrees of latitude is roughly 2200ft, well over the 500ft
        # cutoff
        3: {"lon": -72.8, "lat": 43.406},
    }

    items = {
        "a1": {"id": "a1", "nodes": [1, 2], "name": "Real Name"},
        "a2": {"id": "a2", "nodes": [2, 3], "name": ""},
    }

    merged = osm_processor_instance._merge_multi_route_clusters(items, ["name"])

    assert merged == items


def test_get_center(osm_file):
    osm_processor = OSMProcessor(osm_file)

    # A multi_route trail's junction nodes are intentionally double-counted
    # (once as the end of one branch, once as the start of the next -- see
    # _merge_multi_route_clusters' split_at_junctions), nudging the
    # centroid by a couple of meters versus counting each node once
    actual_center = Point(-72.73655514298721, 43.41027425591992)

    assert osm_processor.get_center() == actual_center


def test_get_state(osm_file):
    osm_processor = OSMProcessor(osm_file)

    state = osm_processor.get_state()

    assert state == State("VT")


def test_get_direction(osm_file):
    osm_processor = OSMProcessor(osm_file)

    direction = osm_processor.get_direction()

    assert direction == "w"
