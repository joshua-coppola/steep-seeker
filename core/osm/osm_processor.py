import shapely

from core.osm.osm_reader import OSMHandler
from core.osm.trail_parser import identify_trails, identify_lifts


## Todo: create get trail, lift support with shapely, handle multiline relations


class OSMProcessor:
    """
    Accepts an OSM file which is then parsed into trails and lifts.

    The trails and lifts are stored in dicts of the same name.
    """

    def __init__(self, filename: str):
        osm_handler = OSMHandler()
        osm_handler.apply_file(filename)

        self.nodes = osm_handler.nodes
        self.ways = osm_handler.ways
        self.relations = osm_handler.relations

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
            for way_id in relation_value.get("members"):
                way = self.trails[way_id]
                for key in trail_info.keys():
                    if key == "id":
                        trail_info[key].append(way_id)
                    else:
                        trail_info[key].append(way[key])

            same_values = 0
            for key in trail_info.keys():
                if key == "nodes" or key == "id":
                    continue
                if len(set(trail_info[key])) == 1:
                    same_values += 1

            if not same_values == 6:
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
            for existing_trail in complete_trails.keys():
                matching_parts = 0
                for key in complete_trails[existing_trail].keys():
                    # skip the unique parts
                    if key == "id" or key == "nodes":
                        continue
                    if trail_value[key] == complete_trails[existing_trail][key]:
                        matching_parts += 1

                # if all metadata is matching, then check if the start/end points line up
                if matching_parts == 6:
                    if (
                        trail_value["nodes"][0]
                        == complete_trails[existing_trail]["nodes"][-1]
                    ):
                        complete_trails[existing_trail]["nodes"] += trail_value[
                            "nodes"
                        ][1:]
                    elif (
                        trail_value["nodes"][-1]
                        == complete_trails[existing_trail]["nodes"][0]
                    ):
                        complete_trails[existing_trail]["nodes"] = (
                            trail_value["nodes"][:-1]
                            + complete_trails[existing_trail]["nodes"]
                        )
                    else:
                        continue
                    found_match = True

            if not found_match:
                complete_trails[trail_id] = trail_value

        self.trails = complete_trails

    def get_trails(self):
        trail_objects = {}
        for trail_id in self.trails:
            trail = self.trails[trail_id]
            nodes = trail["nodes"]
            node_array = []
            for node in nodes:
                point = shapely.Point(self.nodes[node]["lon"], self.nodes[node]["lat"])
                node_array.append(point)

            if not trail["area"]:
                trail_points = shapely.LineString(node_array)
            else:
                trail_points = shapely.Polygon(node_array)

            trail_objects[trail_id] = {}
            trail_objects[trail_id]["geometry"] = trail_points

            for key in trail.keys():
                if key == "nodes":
                    continue
                trail_objects[trail_id][key] = trail[key]

        return trail_objects

    def get_lifts(self):
        lift_objects = {}
        for lift_id in self.lifts:
            lift = self.lifts[lift_id]
            nodes = lift["nodes"]
            node_array = []
            for node in nodes:
                point = shapely.Point(self.nodes[node]["lon"], self.nodes[node]["lat"])
                node_array.append(point)

            lift_points = shapely.LineString(node_array)

            lift_objects[lift_id] = {}
            lift_objects[lift_id]["geometry"] = lift_points

            for key in lift.keys():
                if key == "nodes":
                    continue
                lift_objects[lift_id][key] = lift[key]

        return lift_objects
