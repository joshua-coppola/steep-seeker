from core.osm.osm_reader import OSMHandler
from core.osm.trail_parser import identify_trails, identify_lifts

## Todo: merge trail support


class OSMProcessor:
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

        self.deduplicate_trails()

    def deduplicate_trails(self):
        for relation_id, relation_value in self.trail_relations.items():
            if len(relation_value.get("members")) == 1:
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

            to_be_merged = [trail_info["id"][0]]
            for i in range(len(trail_info["nodes"]) - 1):
                if trail_info["nodes"][i][-1] == trail_info["nodes"][i + 1][0]:
                    to_be_merged.append(trail_info["id"][i + 1])

            if len(to_be_merged) == 1:
                continue

            merged_nodes = []
            for way_id in to_be_merged:
                merged_nodes += self.trails[way_id]["nodes"]

            merged_nodes = list(dict.fromkeys(merged_nodes))
            keeper_id = to_be_merged[0]

            self.trails[keeper_id]["nodes"] = merged_nodes

            for way_id in to_be_merged[1:]:
                del self.trails[way_id]
