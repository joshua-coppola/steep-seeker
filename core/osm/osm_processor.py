import uuid
from collections import defaultdict
from math import atan2, degrees

import shapely
from united_states import UnitedStates

from core.connectors.elevation_api import Elevation
from core.datamodels.state import State
from core.osm.osm_reader import OSMHandler
from core.osm.trail_parser import identify_hikes, identify_lifts, identify_trails
from core.support.area_routes import get_area_route
from core.support.lift import Lift
from core.support.multi_route import get_multi_route
from core.support.trail import Trail
from core.support.utils import (
    compute_geometry_stats,
    get_average_slope,
    get_length,
    get_max_slope,
    get_steepest_pitch,
    get_vertical_drop,
    meters_to_feet,
    polygon_interior_grid,
    space_line_points_evenly,
    space_polygon_exterior_points_evenly,
)

## Todo: handle multiline relations

STEEPEST_PITCH_WINDOWS_FEET = (100, 150, 300, 500, 1320, 2640, 5280)

# Fields (besides id/nodes) that every member of a relation, or every
# candidate pair in a merge pass, must agree on before flatten/merge treats
# them as segments of the same feature. hazardous is deliberately excluded
# for trails -- it's always False at parse time (only set later via the
# management popup), so it shouldn't gate whether two segments are "the
# same trail".
TRAIL_MATCH_FIELDS = ["name", "official_rating", "gladed", "area", "ungroomed", "park"]
HIKE_MATCH_FIELDS = ["name"]

# _merge_multi_route_clusters lets an unnamed way ride into a named cluster
# (OSM often only tags one branch of a forking trail), but only when it's
# short -- an unnamed way touching a named trail's endpoint is frequently a
# genuinely separate, merely nameless, trail or connector, and blindly
# folding in a long one would produce a "branch" that isn't really part of
# the run at all.
MULTI_ROUTE_UNNAMED_MAX_LENGTH_FEET = 500


class OSMProcessor:
    """
    Accepts an OSM file which is then parsed into trails and lifts.

    The trails and lifts are stored in dicts of the same name.
    """

    def __init__(self, filename: str, mountain_id: str | None = None):
        osm_handler = OSMHandler()
        osm_handler.apply_file(filename)

        self.nodes = osm_handler.nodes
        self.ways = osm_handler.ways
        self.relations = osm_handler.relations
        self.mountain_id = mountain_id
        if not self.mountain_id:
            # generate a UUID based on the latiude/longitude and name of the mountain
            node = self.nodes[next(iter(self.nodes))]
            mountain_name = filename.split("/")[-1].split(".osm")[0]

            # multiply the lat/lon by 10 so it is slightly more percise than rounding
            # to the nearest int without being easily shifted by a slighly different
            # first node
            identifier = (
                f"{(int(node['lon'] * 10), int(node['lat'] * 10))} {mountain_name}"
            )
            self.mountain_id = uuid.uuid3(uuid.NAMESPACE_OID, identifier)

        trail_dict = identify_trails(self.ways, self.relations)
        self.trails = trail_dict["trails"]
        self.trail_relations = trail_dict["relations"]

        lift_dict = identify_lifts(self.ways)
        self.lifts = lift_dict["lifts"]

        hike_dict = identify_hikes(self.ways, self.relations)
        self.hikes = hike_dict["hikes"]
        self.hike_relations = hike_dict["relations"]

        self.trails, self.trail_relations = self._flatten_relations(
            self.trails, self.trail_relations, TRAIL_MATCH_FIELDS
        )
        self.trails = self._merge_line_features(self.trails, TRAIL_MATCH_FIELDS)
        self.trails = self._merge_multi_route_clusters(self.trails, TRAIL_MATCH_FIELDS)

        # Kept scoped to self.hikes alone, merged into self.lifts only
        # afterward: running the adjacency-merge over the combined self.lifts
        # would risk splicing two distinct real lifts together if they share
        # a station node and have identical (all-None) metadata. Way ids are
        # globally unique in OSM, so this update is collision-safe.
        self.hikes, self.hike_relations = self._flatten_relations(
            self.hikes, self.hike_relations, HIKE_MATCH_FIELDS
        )
        self.hikes = self._merge_line_features(self.hikes, HIKE_MATCH_FIELDS)
        self.lifts.update(self.hikes)

    def _flatten_relations(
        self, items: dict, relations: dict, match_fields: list[str]
    ) -> tuple[dict, dict]:
        """
        Converts any relationships that can be represented as a single line
        into a single item, then removes the relationship. match_fields is
        the set of metadata keys (besides id/nodes) that every member must
        agree on for the relation to be flattened. Returns the updated
        (items, relations).
        """
        merged_relation_ids = []
        for relation_id, relation_value in relations.items():
            if len(relation_value.get("members")) == 1:
                merged_relation_ids.append(relation_id)
                continue

            # Some member ways get filtered out during identification (wrong
            # piste:type, excluded tags, etc.) or fall outside the downloaded
            # extract, so they never make it into items. Drop those
            # members; if fewer than two remain there's nothing to merge.
            members = [
                way_id for way_id in relation_value.get("members") if way_id in items
            ]
            if len(members) < 2:
                continue

            info = {"id": [], "nodes": [], **{key: [] for key in match_fields}}
            for way_id in members:
                way = items[way_id]
                for key, value_list in info.items():
                    if key == "id":
                        value_list.append(way_id)
                    else:
                        value_list.append(way[key])

            same_values = 0
            for key, value_list in info.items():
                if key == "nodes" or key == "id":
                    continue
                if len(set(value_list)) == 1:
                    same_values += 1

            if same_values != len(match_fields):
                continue

            to_be_merged = [
                {
                    "id": info["id"][0],
                    "start": info["nodes"][0][0],
                    "end": info["nodes"][0][-1],
                }
            ]

            for i in range(len(info["nodes"]) - 1):
                nodes = info["nodes"][i + 1]
                if nodes[0] == to_be_merged[-1]["end"]:
                    to_be_merged.append(
                        {
                            "id": info["id"][i + 1],
                            "start": info["nodes"][i + 1][0],
                            "end": info["nodes"][i + 1][-1],
                        }
                    )
                elif nodes[-1] == to_be_merged[0]["start"]:
                    to_be_merged.insert(
                        0,
                        {
                            "id": info["id"][i + 1],
                            "start": info["nodes"][i + 1][0],
                            "end": info["nodes"][i + 1][-1],
                        },
                    )

            if len(to_be_merged) == 1:
                continue

            merged_nodes = []
            for way_id in to_be_merged:
                merged_nodes += items[way_id["id"]]["nodes"]

            merged_nodes = list(dict.fromkeys(merged_nodes))
            keeper_id = to_be_merged[0]["id"]

            items[keeper_id]["nodes"] = merged_nodes

            for way_id in to_be_merged[1:]:
                del items[way_id["id"]]

            merged_relation_ids.append(relation_id)

        for relation_id in merged_relation_ids:
            del relations[relation_id]

        return items, relations

    def _merge_line_features(self, items: dict, match_fields: list[str]) -> dict:
        """
        Merges any items that agree on every field in match_fields and have
        an overlapping start/end point. Returns the merged items.

        This loops until no more merges occur.
        """
        merged_any = True
        while merged_any:
            items, merged_any = self._merge_line_features_pass(items, match_fields)
        return items

    def _merge_line_features_pass(
        self, items: dict, match_fields: list[str]
    ) -> tuple[dict, bool]:
        """
        One merge pass over items; returns (merged items, whether anything merged).
        """
        complete_items = {}
        merged_any = False

        for item_id, item_value in items.items():
            found_match = False
            for existing_data in complete_items.values():
                matching_parts = sum(
                    1 for key in match_fields if item_value[key] == existing_data[key]
                )

                # if all metadata is matching, then check if the start/end points line up
                if matching_parts == len(match_fields):
                    if item_value["nodes"][0] == existing_data["nodes"][-1]:
                        existing_data["nodes"] = (
                            existing_data["nodes"] + item_value["nodes"][1:]
                        )
                    elif item_value["nodes"][-1] == existing_data["nodes"][0]:
                        existing_data["nodes"] = (
                            item_value["nodes"][:-1] + existing_data["nodes"]
                        )
                    else:
                        continue
                    found_match = True
                    merged_any = True
                    # item_value now belongs to existing_data -- stop
                    # checking it against the other accumulated items, or
                    # its nodes would get folded into more than one of them
                    break

            if not found_match:
                complete_items[item_id] = item_value

        return complete_items, merged_any

    def _merge_multi_route_clusters(self, items: dict, match_fields: list[str]) -> dict:
        """
        Finds trails left un-merged by _merge_line_features that are
        actually branches of the same run -- splitting off and/or rejoining
        -- rather than genuinely separate trails: two items agreeing on
        every match_fields value are grouped together if either one's start
        or end node lands anywhere along the other's node list, not just at
        the other's own start/end (the narrower rule _merge_line_features
        applies). A pure chain always fully collapses in that prior pass
        regardless of dict iteration order, so anything still grouped here
        by more than one member is a genuine fork, not a chain that pass
        missed.

        "name" (when present in match_fields) is treated specially: an
        unnamed way (OSM often only tags one branch of a forking trail with
        its name) is compatible with any name, but two *differently* named
        ways never end up in the same cluster -- not even indirectly, via a
        shared unnamed way that would otherwise bridge them both (a real
        hazard at a trail junction, where an unnamed connector/crossing
        piece can touch two unrelated named trails at once). Every other
        match_fields value still needs exact equality, same as
        _merge_line_features.

        An unnamed way is further only eligible to merge in at all when its
        own length is under MULTI_ROUTE_UNNAMED_MAX_LENGTH_FEET -- a long
        unnamed way touching a named trail's endpoint is more likely a
        distinct, merely nameless, trail than an actual branch of it. A
        named way is never subject to this length check.

        Each resulting cluster of 2+ items collapses into one trail dict
        that keeps the first member's id and match_fields values (except
        name -- a non-empty name among the cluster's members wins over an
        empty one), drops "nodes" in favor of "branches", and sets
        "multi_route" True. A cluster of one item is returned as-is.

        A member whose touch point is at the *other* item's endpoint needs
        no further work -- its own node list becomes one branch. But when
        the touch is at an interior point (a spur splitting off partway
        through a longer way, not at either way's own end), that interior
        node isn't a real vertex of the resampled geometry _build_trail_geometry
        will later produce for the branch that merely passes through it --
        space_line_points_evenly only guarantees a line's own first/last
        input vertex survives resampling exactly, not an arbitrary interior
        one. Left alone, that would leave the two branches' resampled
        geometries not sharing an exact coordinate at their real-world
        junction, which multi_route.py's graph builder depends on to treat
        them as connected. So every member's node list is first split at
        each interior occurrence of any cluster member's endpoint, turning
        "branches" into a flat list of pure graph edges whose own
        start/end are always a real, shared junction node.
        """
        grouping_fields = [field for field in match_fields if field != "name"]
        match_by_name = "name" in match_fields

        by_match_fields = defaultdict(list)
        for item_id, item in items.items():
            # Area trails (glades/bowls, sampled as a polygon) are never
            # multi-route candidates -- a "branches" MultiLineString and a
            # Polygon boundary are fundamentally different geometry shapes,
            # and _build_trail_geometry can only build one or the other.
            # Two area ways happening to touch is a question for
            # _merge_line_features's existing polygon-ring merge, not this
            # pass.
            if item.get("area"):
                continue
            by_match_fields[tuple(item[field] for field in grouping_fields)].append(
                item_id
            )

        parent = {item_id: item_id for item_id in items}
        # Tracks each component root's established name -- None while every
        # member merged into it so far is unnamed. Checked (and updated) on
        # every union, so a merge that would fuse two components that
        # already settled on two different non-empty names is refused, no
        # matter how many unnamed ways sit between them.
        component_name = {
            item_id: (items[item_id]["name"] if match_by_name else None) or None
            for item_id in items
        }

        def find(item_id: str) -> str:
            while parent[item_id] != item_id:
                parent[item_id] = parent[parent[item_id]]
                item_id = parent[item_id]
            return item_id

        def is_mergeable(item_id: str) -> bool:
            if not match_by_name or items[item_id]["name"]:
                return True
            return (
                self._way_length_feet(items[item_id]["nodes"])
                < MULTI_ROUTE_UNNAMED_MAX_LENGTH_FEET
            )

        def try_union(a_id: str, b_id: str) -> None:
            root_a, root_b = find(a_id), find(b_id)
            if root_a == root_b:
                return
            if match_by_name:
                name_a, name_b = component_name[root_a], component_name[root_b]
                if name_a and name_b and name_a != name_b:
                    return
            if not is_mergeable(a_id) or not is_mergeable(b_id):
                return
            parent[root_a] = root_b
            if match_by_name:
                component_name[root_b] = (
                    component_name[root_b] or component_name[root_a]
                )

        def touches(a_nodes: list, b_nodes: list) -> bool:
            b_set = set(b_nodes)
            if a_nodes[0] in b_set or a_nodes[-1] in b_set:
                return True
            a_set = set(a_nodes)
            return b_nodes[0] in a_set or b_nodes[-1] in a_set

        def split_at_junctions(nodes: list, junctions: set) -> list[list]:
            segments = []
            current = [nodes[0]]
            for node in nodes[1:]:
                current.append(node)
                if node in junctions and len(current) > 1:
                    segments.append(current)
                    current = [node]
            if len(current) > 1:
                segments.append(current)
            return segments

        for group_ids in by_match_fields.values():
            for i, a_id in enumerate(group_ids):
                for b_id in group_ids[i + 1 :]:
                    if touches(items[a_id]["nodes"], items[b_id]["nodes"]):
                        try_union(a_id, b_id)

        clusters = defaultdict(list)
        for item_id in items:
            clusters[find(item_id)].append(item_id)

        merged = {}
        for member_ids in clusters.values():
            if len(member_ids) == 1:
                (only_id,) = member_ids
                merged[only_id] = items[only_id]
                continue

            keeper_id = member_ids[0]
            keeper = {
                key: value for key, value in items[keeper_id].items() if key != "nodes"
            }
            keeper["id"] = keeper_id
            keeper["multi_route"] = True

            junctions = set()
            for member_id in member_ids:
                nodes = items[member_id]["nodes"]
                junctions.add(nodes[0])
                junctions.add(nodes[-1])
            branches = []
            for member_id in member_ids:
                branches.extend(
                    split_at_junctions(items[member_id]["nodes"], junctions)
                )
            keeper["branches"] = branches

            if match_by_name:
                keeper["name"] = next(
                    (
                        items[member_id]["name"]
                        for member_id in member_ids
                        if items[member_id]["name"]
                    ),
                    "",
                )
            merged[keeper_id] = keeper

        return merged

    def _node_points(self, nodes: list) -> list[shapely.Point]:
        """
        Maps a list of OSM node ids to shapely Points in (lon, lat) order.
        """
        return [
            shapely.Point(self.nodes[node]["lon"], self.nodes[node]["lat"])
            for node in nodes
        ]

    def _way_length_feet(self, nodes: list) -> float:
        """
        Haversine length, in feet, of a raw OSM node id list -- used by
        _merge_multi_route_clusters to gate merging in an unnamed way before
        any elevation lookup or resampling has happened.
        """
        points = self._node_points(nodes)
        coordinates = [[point.x, point.y] for point in points]
        return meters_to_feet(get_length({"coordinates": coordinates}))

    def _build_trail_geometry(
        self, trail: dict
    ) -> tuple[
        shapely.LineString | shapely.Polygon | shapely.MultiLineString,
        shapely.MultiPoint | None,
    ]:
        """
        Builds a trail's evenly-spaced geometry (and, for area trails, the
        interior sample grid) without any elevation lookups. Returns
        (geometry, interior_multipoint); interior_multipoint is only set for
        area trails.
        """
        if trail.get("multi_route"):
            branch_lines = [
                space_line_points_evenly(shapely.LineString(self._node_points(branch)))
                for branch in trail["branches"]
            ]
            return shapely.MultiLineString(branch_lines), None

        node_array = self._node_points(trail["nodes"])
        if not trail["area"]:
            return space_line_points_evenly(shapely.LineString(node_array)), None

        geometry = space_polygon_exterior_points_evenly(shapely.Polygon(node_array))
        return geometry, polygon_interior_grid(geometry)

    def _elevation_populated_branches(
        self, geometry: shapely.MultiLineString, elevation_api: Elevation
    ) -> list[list[tuple[float, float, float]]]:
        """
        Looks up elevation for a multi-route trail's branches in a single
        batched call (rather than one call per branch), then splits the
        flat result back out per branch. A single call matters beyond just
        request count: two branches sharing a fork/rejoin junction node
        must resolve to the exact same elevation there for multi_route.py's
        exact-coordinate graph dedup to treat them as one graph node, which
        only the real elevation API's cache -- keyed by coordinate, shared
        across calls -- guarantees if it's queried once for both branches
        together.
        """
        branch_lines = list(geometry.geoms)
        lengths = [len(line.coords) for line in branch_lines]
        flat_points = elevation_api.get(
            [point for line in branch_lines for point in line.coords]
        )

        branches = []
        offset = 0
        for length in lengths:
            branches.append(flat_points[offset : offset + length])
            offset += length
        return branches

    def get_trails(self) -> dict[str, Trail]:
        """
        Transforms the trails dict into a standardized format for the rest of
        SteepSeeker. This takes the form of removing references to nodes and
        instead using a geojson string and using the Trail class for each
        trail in the dict. Returns a dict of Trail objects where the dict keys
        are the trail IDs.

        Elevation is fetched up front so the assembly loop never touches the
        API: phase 1 builds every trail's spaced geometry, phase 2 resolves
        every elevation lookup (a batched lookup over all trail geometry,
        then the area-trail routed centerlines, whose points aren't known
        until the route is computed from that now-cached elevation), and
        phase 3 assembles each Trail entirely from cache. This keeps the
        elevation API request count at ~ceil(points / batch) instead of one
        request per trail, and keeps a single progress bar active at a time.
        """
        trail_objects = {}
        elevation_api = Elevation()

        # Phase 1: build every trail's spaced geometry, no elevation lookups.
        trail_geometries = {
            trail_id: self._build_trail_geometry(trail)
            for trail_id, trail in self.trails.items()
        }

        # Phase 2a: one batched elevation lookup over all trail geometry.
        prefetch_points = []
        for trail_id, (geometry, interior_multipoint) in trail_geometries.items():
            if self.trails[trail_id]["area"]:
                prefetch_points.extend(geometry.exterior.coords)
                prefetch_points.extend(
                    point.coords[0] for point in interior_multipoint.geoms
                )
            else:
                # shapely.get_coordinates flattens either a plain LineString
                # or a multi-route trail's MultiLineString, so this one
                # branch covers both
                prefetch_points.extend(shapely.get_coordinates(geometry))
        elevation_api.get(prefetch_points)

        # Phase 2b: route each area/multi-route trail (elevation for its raw
        # geometry is now cached), then batch-fetch elevation for every
        # routed centerline in one shared call.
        computed_routes = {}
        area_trail_ids = [tid for tid in self.trails if self.trails[tid]["area"]]
        multi_route_trail_ids = [
            tid for tid in self.trails if self.trails[tid].get("multi_route")
        ]
        if area_trail_ids or multi_route_trail_ids:
            route_points = []
            for trail_id in area_trail_ids:
                geometry, interior_multipoint = trail_geometries[trail_id]
                exterior_json = {
                    "coordinates": [elevation_api.get(list(geometry.exterior.coords))]
                }
                interior_json = {
                    "coordinates": elevation_api.get(
                        [point.coords[0] for point in interior_multipoint.geoms]
                    )
                }
                raw_route = get_area_route(exterior_json, interior_json)
                route_line = space_line_points_evenly(
                    shapely.LineString(
                        [(point[0], point[1]) for point in raw_route["coordinates"]]
                    )
                )
                computed_routes[trail_id] = route_line
                route_points.extend(route_line.coords)

            for trail_id in multi_route_trail_ids:
                geometry, _interior_multipoint = trail_geometries[trail_id]
                branches = self._elevation_populated_branches(geometry, elevation_api)
                raw_route = get_multi_route(branches)
                # re-spaced (like area's route) for uniform stats-window
                # density -- not smoothed, since these are real mapped
                # nodes, not a synthetic sampled grid
                route_line = space_line_points_evenly(
                    shapely.LineString(
                        [(point[0], point[1]) for point in raw_route["coordinates"]]
                    )
                )
                computed_routes[trail_id] = route_line
                route_points.extend(route_line.coords)

            elevation_api.get(route_points)

        # Phase 3: assemble each Trail entirely from cached elevation.
        for trail_id in self.trails:
            trail = self.trails[trail_id]
            geometry, interior_multipoint = trail_geometries[trail_id]

            interior_geometry = None
            route = None

            if trail["area"]:
                geometry_json = {
                    "coordinates": [elevation_api.get(list(geometry.exterior.coords))]
                }
                interior_geometry = {
                    "coordinates": elevation_api.get(
                        [point.coords[0] for point in interior_multipoint.geoms]
                    )
                }
                route = {
                    "coordinates": elevation_api.get(
                        list(computed_routes[trail_id].coords)
                    )
                }
            elif trail.get("multi_route"):
                geometry_json = {
                    "coordinates": self._elevation_populated_branches(
                        geometry, elevation_api
                    )
                }
                route = {
                    "coordinates": elevation_api.get(
                        list(computed_routes[trail_id].coords)
                    )
                }
            else:
                geometry_json = {
                    "coordinates": elevation_api.get(list(geometry.coords))
                }

            # Use route for areas/multi-route trails since neither's raw
            # geometry is where people actually ski
            stats_geometry = route if route is not None else geometry_json

            trail_dict = {}
            trail_dict["trail_id"] = trail["id"]
            trail_dict["mountain_id"] = self.mountain_id
            stats = compute_geometry_stats(stats_geometry)
            trail_dict["length"] = get_length(stats_geometry, stats=stats)
            trail_dict["vertical"] = get_vertical_drop(geometry_json)
            trail_dict["max_slope"] = get_max_slope(stats_geometry, stats=stats)
            trail_dict["average_slope"] = get_average_slope(stats_geometry, stats=stats)
            for window_feet in STEEPEST_PITCH_WINDOWS_FEET:
                trail_dict[f"steepest_{window_feet}ft"] = get_steepest_pitch(
                    stats_geometry, window_feet, cumulative_dist=stats.cumulative_dist
                )

            # geometry_json/interior_geometry/route are geojson blobs (the
            # format utils.py's stat helpers and get_area_route expect);
            # Trail's fields are real shapely geometries so they round-trip
            # through to_db/from_db as WKT
            if trail["area"]:
                trail_dict["geometry"] = shapely.Polygon(
                    geometry_json["coordinates"][0]
                )
            elif trail.get("multi_route"):
                trail_dict["geometry"] = shapely.MultiLineString(
                    [
                        shapely.LineString(branch)
                        for branch in geometry_json["coordinates"]
                    ]
                )
            else:
                trail_dict["geometry"] = shapely.LineString(
                    geometry_json["coordinates"]
                )
            trail_dict["interior_geometry"] = (
                shapely.MultiPoint(interior_geometry["coordinates"])
                if interior_geometry
                else None
            )
            trail_dict["route"] = (
                shapely.LineString(route["coordinates"]) if route else None
            )

            for key in trail:
                if key in ("nodes", "id", "branches"):
                    continue
                trail_dict[key] = trail[key]

            trail = Trail(**trail_dict)
            trail_objects[trail_id] = trail

        return trail_objects

    def get_lifts(self) -> dict[str, Lift]:
        """
        Transforms the lifts dict into a standardized format for the rest of
        SteepSeeker. This takes the form of removing references to nodes and
        instead using a geojson string and using the Lift class for each
        lift in the dict. Returns a dict of Lift objects where the dict keys
        are the lift IDs.

        Like get_trails, elevation is fetched in two phases: every lift's
        spaced geometry is built and batch-looked-up once to warm the cache,
        then each Lift is assembled from cached elevation.
        """
        elevation_api = Elevation()
        lift_objects = {}

        # Phase 1: build every lift's spaced geometry, no elevation lookups.
        lift_geometries = {
            lift_id: space_line_points_evenly(
                shapely.LineString(self._node_points(lift["nodes"]))
            )
            for lift_id, lift in self.lifts.items()
        }

        # Phase 2: one batched elevation lookup to warm the cache.
        prefetch_points = []
        for geometry in lift_geometries.values():
            prefetch_points.extend(geometry.coords)
        elevation_api.get(prefetch_points)

        # Phase 3: assemble each Lift; elevation now comes from the cache.
        for lift_id in self.lifts:
            lift = self.lifts[lift_id]
            geometry = lift_geometries[lift_id]
            geometry_json = {"coordinates": elevation_api.get(list(geometry.coords))}

            lift_dict = {}
            lift_dict["lift_id"] = lift["id"]
            # geometry_json is a geojson blob (the format utils.py's stat
            # helpers expect); Lift.geometry is a real shapely LineString so
            # it round-trips through to_db/from_db as WKT
            lift_dict["geometry"] = shapely.LineString(geometry_json["coordinates"])
            lift_dict["mountain_id"] = self.mountain_id
            lift_stats = compute_geometry_stats(geometry_json)
            lift_dict["length"] = get_length(geometry_json, stats=lift_stats)
            lift_dict["vertical"] = get_vertical_drop(geometry_json)
            lift_dict["average_slope"] = get_average_slope(
                geometry_json, stats=lift_stats
            )

            for key in lift:
                if key == "nodes" or key == "id":
                    continue
                lift_dict[key] = lift[key]

            lift = Lift(**lift_dict)
            lift_objects[lift_id] = lift

        return lift_objects

    def get_center(self) -> shapely.Point:
        """
        Calculates the centroid of the mountain from all trail points
        and returns a shapely Point
        """
        if not self.nodes:
            raise ValueError("No nodes found")

        node_array = []
        for trail_id in self.trails:
            trail = self.trails[trail_id]
            if trail.get("multi_route"):
                nodes = [node for branch in trail["branches"] for node in branch]
            else:
                nodes = trail["nodes"]

            node_array += [
                shapely.Point(self.nodes[node]["lon"], self.nodes[node]["lat"])
                for node in nodes
            ]

        return shapely.MultiPoint(node_array).centroid

    def get_state(self) -> State:
        """
        Gets the US State that the OSM file is in. Finds the center of the
        nodes then returns that State
        """
        center = self.get_center()

        us = UnitedStates()
        state_info = us.from_coords(center.y, center.x)

        if state_info:
            return State(state_info[0].abbr)
        else:
            raise ValueError("No US State found")

    def get_direction(self) -> str:
        """
        Gets cardinal direction that most trails
        follow. Will be one of the following: n,s,e,w
        """
        headings = []

        for trail in self.trails.values():
            # a multi-route trail has no single ordered path -- its first
            # branch's endpoints are a fine stand-in, since this is only a
            # coarse mountain-wide average
            nodes = trail["branches"][0] if trail.get("multi_route") else trail["nodes"]
            start_id = nodes[0]
            end_id = nodes[-1]

            start_node = self.nodes[start_id]
            end_node = self.nodes[end_id]

            dx = start_node["lon"] - end_node["lon"]
            dy = start_node["lat"] - end_node["lat"]

            headings.append(degrees(atan2(dx, dy)))

        if not headings:
            return None  # or raise an error if appropriate

        avg_heading = sum(headings) / len(headings)

        abs_heading = abs(avg_heading)
        if abs_heading < 45:
            return "n"
        elif abs_heading > 135:
            return "s"
        elif avg_heading > 0:
            return "e"
        else:
            return "w"
