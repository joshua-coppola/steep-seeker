import uuid
from math import atan2, degrees

import shapely
from united_states import UnitedStates

from core.connectors.elevation_api import Elevation
from core.datamodels.state import State
from core.osm.osm_reader import OSMHandler
from core.osm.trail_parser import identify_lifts, identify_trails
from core.support.area_routes import get_area_route
from core.support.lift import Lift
from core.support.trail import Trail
from core.support.utils import (
    get_average_slope,
    get_length,
    get_max_slope,
    get_steepest_pitch,
    get_vertical_drop,
    polygon_interior_grid,
    space_line_points_evenly,
    space_polygon_exterior_points_evenly,
)

## Todo: handle multiline relations

STEEPEST_PITCH_WINDOWS_METERS = (30, 50, 100, 200, 500, 1000)


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

        self.flatten_relations()
        self.merge_trails()

    def flatten_relations(self) -> None:
        """
        Converts any relationships that can be represented as a single line
        into a single trail, then removes the relationship. Updates the
        self.trail_relations and self.trails in place.
        """
        merged_relation_ids = []
        for relation_id, relation_value in self.trail_relations.items():
            if len(relation_value.get("members")) == 1:
                merged_relation_ids.append(relation_id)
                continue

            # Some member ways get filtered out by identify_trails (wrong
            # piste:type, excluded tags, etc.) or fall outside the downloaded
            # extract, so they never make it into self.trails. Drop those
            # members; if fewer than two remain there's nothing to merge.
            members = [
                way_id
                for way_id in relation_value.get("members")
                if way_id in self.trails
            ]
            if len(members) < 2:
                continue

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
            for way_id in members:
                way = self.trails[way_id]
                for key, value_list in trail_info.items():
                    if key == "id":
                        value_list.append(way_id)
                    else:
                        value_list.append(way[key])

            same_values = 0
            for key, value_list in trail_info.items():
                if key == "nodes" or key == "id":
                    continue
                if len(set(value_list)) == 1:
                    same_values += 1

            if same_values != 6:
                continue

            to_be_merged = [
                {
                    "id": trail_info["id"][0],
                    "start": trail_info["nodes"][0][0],
                    "end": trail_info["nodes"][0][-1],
                }
            ]

            for i in range(len(trail_info["nodes"]) - 1):
                nodes = trail_info["nodes"][i + 1]
                if nodes[0] == to_be_merged[-1]["end"]:
                    to_be_merged.append(
                        {
                            "id": trail_info["id"][i + 1],
                            "start": trail_info["nodes"][i + 1][0],
                            "end": trail_info["nodes"][i + 1][-1],
                        }
                    )
                elif nodes[-1] == to_be_merged[0]["start"]:
                    to_be_merged.insert(
                        0,
                        {
                            "id": trail_info["id"][i + 1],
                            "start": trail_info["nodes"][i + 1][0],
                            "end": trail_info["nodes"][i + 1][-1],
                        },
                    )

            if len(to_be_merged) == 1:
                continue

            merged_nodes = []
            for way_id in to_be_merged:
                merged_nodes += self.trails[way_id["id"]]["nodes"]

            merged_nodes = list(dict.fromkeys(merged_nodes))
            keeper_id = to_be_merged[0]["id"]

            self.trails[keeper_id]["nodes"] = merged_nodes

            for way_id in to_be_merged[1:]:
                del self.trails[way_id["id"]]

            merged_relation_ids.append(relation_id)

        for id in merged_relation_ids:
            del self.trail_relations[id]

    def merge_trails(self) -> None:
        """
        Merges any trails that have the same metadata and have an overlapping
        start/end point. Updates the self.trails object with the new trail list.
        """
        start_dict = {}
        end_dict = {}

        complete_trails = {}

        for trail_id, trail_value in self.trails.items():
            start_dict[trail_value["nodes"][0]] = trail_id
            end_dict[trail_value["nodes"][-1]] = trail_id

        for trail_id, trail_value in self.trails.items():
            found_match = False
            for existing_data in complete_trails.values():
                matching_parts = 0
                for key, value in existing_data.items():
                    # skip the unique parts
                    if key == "id" or key == "nodes":
                        continue
                    if trail_value[key] == value:
                        matching_parts += 1

                # if all metadata is matching, then check if the start/end points line up
                if matching_parts == 6:
                    if trail_value["nodes"][0] == existing_data["nodes"][-1]:
                        existing_data["nodes"] += trail_value["nodes"][1:]
                    elif trail_value["nodes"][-1] == existing_data["nodes"][0]:
                        existing_data["nodes"] = (
                            trail_value["nodes"][:-1] + existing_data["nodes"]
                        )
                    else:
                        continue
                    found_match = True

            if not found_match:
                complete_trails[trail_id] = trail_value

        self.trails = complete_trails

    def _node_points(self, nodes: list) -> list[shapely.Point]:
        """
        Maps a list of OSM node ids to shapely Points in (lon, lat) order.
        """
        return [
            shapely.Point(self.nodes[node]["lon"], self.nodes[node]["lat"])
            for node in nodes
        ]

    def _build_trail_geometry(
        self, trail: dict
    ) -> tuple[shapely.LineString | shapely.Polygon, shapely.MultiPoint | None]:
        """
        Builds a trail's evenly-spaced geometry (and, for area trails, the
        interior sample grid) without any elevation lookups. Returns
        (geometry, interior_multipoint); interior_multipoint is None for
        non-area trails.
        """
        node_array = self._node_points(trail["nodes"])
        if not trail["area"]:
            return space_line_points_evenly(shapely.LineString(node_array)), None

        geometry = space_polygon_exterior_points_evenly(shapely.Polygon(node_array))
        return geometry, polygon_interior_grid(geometry)

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
            if not self.trails[trail_id]["area"]:
                prefetch_points.extend(geometry.coords)
            else:
                prefetch_points.extend(geometry.exterior.coords)
                prefetch_points.extend(
                    point.coords[0] for point in interior_multipoint.geoms
                )
        elevation_api.get(prefetch_points)

        # Phase 2b: route each area trail (elevation for exterior/interior is
        # now cached), then batch-fetch elevation for every routed centerline.
        area_routes = {}
        area_trail_ids = [tid for tid in self.trails if self.trails[tid]["area"]]
        if area_trail_ids:
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
                area_routes[trail_id] = route_line
                route_points.extend(route_line.coords)
            elevation_api.get(route_points)

        # Phase 3: assemble each Trail entirely from cached elevation.
        for trail_id in self.trails:
            trail = self.trails[trail_id]
            geometry, interior_multipoint = trail_geometries[trail_id]

            interior_geometry = None
            route = None

            if not trail["area"]:
                geometry_json = {
                    "coordinates": elevation_api.get(list(geometry.coords))
                }
            else:
                geometry_json = {
                    "coordinates": [elevation_api.get(list(geometry.exterior.coords))]
                }
                interior_geometry = {
                    "coordinates": elevation_api.get(
                        [point.coords[0] for point in interior_multipoint.geoms]
                    )
                }
                route = {
                    "coordinates": elevation_api.get(list(area_routes[trail_id].coords))
                }

            # Use route for areas since the boundry isn't where people actually ski
            stats_geometry = route if trail["area"] else geometry_json

            trail_dict = {}
            trail_dict["trail_id"] = trail["id"]
            trail_dict["mountain_id"] = self.mountain_id
            trail_dict["length"] = get_length(stats_geometry)
            trail_dict["vertical"] = get_vertical_drop(geometry_json)
            trail_dict["max_slope"] = get_max_slope(stats_geometry)
            trail_dict["average_slope"] = get_average_slope(stats_geometry)
            for window_meters in STEEPEST_PITCH_WINDOWS_METERS:
                trail_dict[f"steepest_{window_meters}m"] = get_steepest_pitch(
                    stats_geometry, window_meters
                )

            # geometry_json/interior_geometry/route are geojson blobs (the
            # format utils.py's stat helpers and get_area_route expect);
            # Trail's fields are real shapely geometries so they round-trip
            # through to_db/from_db as WKT
            if trail["area"]:
                trail_dict["geometry"] = shapely.Polygon(
                    geometry_json["coordinates"][0]
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
                if key == "nodes" or key == "id":
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
            lift_dict["length"] = get_length(geometry_json)
            lift_dict["vertical"] = get_vertical_drop(geometry_json)
            lift_dict["average_slope"] = get_average_slope(geometry_json)

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
            start_id = trail["nodes"][0]
            end_id = trail["nodes"][-1]

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
