def identify_trails(ways, relations):
    """
    Accepts a dict of ways and relations and identifies the valid trails.
    Returns a dict containing the valid trails and relations.
    """
    trails = {}

    valid_types = {"downhill", "traverse", "snow_park", "yes"}
    invalid_name_substrings = ["tubing", "closed", "bike trail"]
    excluded_tags = {"disused", "abandoned", "proposed"}
    invalid_grooming = {"skating", "scooter"}
    ungroomed_grooming = {"backcountry", "mogul", "no"}

    for way_id, way_values in ways.items():
        tags = way_values.get("tags", {})

        trail = {"id": way_id, "nodes": way_values.get("nodes")}

        # Validation: skip invalid piste types
        piste_type = tags.get("piste:type")
        if piste_type not in valid_types:
            continue

        # Skip irrelevant features
        if (
            "mtb:scale:imba" in tags
            or tags.get("landuse") == "grass"
            or excluded_tags.intersection(tags)
        ):
            continue

        # Extract name

        name = tags.get("name")
        piste_name = tags.get("piste:name")
        if piste_name:
            name = piste_name
        if name:
            if any(substr in name.lower() for substr in invalid_name_substrings):
                continue
            trail["name"] = name
        else:
            trail["name"] = ""

        # Official rating
        trail["official_rating"] = tags.get("piste:difficulty")

        # Gladed and area detection
        natural = tags.get("natural", "")
        leaf_type = "leaf:type" in tags

        if tags.get("gladed") == "yes" or "wood" in natural or leaf_type:
            trail["gladed"] = True
        else:
            trail["gladed"] = False

        if "wood" in natural or leaf_type or tags.get("area") == "yes":
            trail["area"] = True
        else:
            trail["area"] = False

        # Ungroomed
        grooming = tags.get("piste:grooming", "")
        if any(g in grooming for g in invalid_grooming):
            continue
        elif any(g in grooming for g in ungroomed_grooming):
            trail["ungroomed"] = True
        else:
            trail["ungroomed"] = False

        # Park
        trail["park"] = piste_type == "snow_park" or "piste:halfpipe" in tags.get(
            "man_made", ""
        )

        trails[way_id] = trail

    trail_relations = {}
    for relation_id, relation_values in relations.items():
        tags = relation_values.get("tags", {})
        trail_relation = {
            "id": relation_id,
            "members": relation_values.get("members"),
            "type": tags.get("type"),
        }

        piste_type = tags.get("piste:type")
        if piste_type not in valid_types:
            continue

        trail_relations[relation_id] = trail_relation

    return {"trails": trails, "relations": trail_relations}


def identify_lifts(ways):
    """
    Accepts a dict of ways and identifies the valid trails.
    Returns a dict containing the valid lifts.
    """
    lifts = {}

    invalid_types = {
        "goods",
        "station",
        "zip line",
        "explosive",
        "abandoned",
        "pylon",
        "disused",
        "proposed",
        "no",
    }

    excluded_tags = {"disused", "abandoned", "proposed"}

    for way_id, way_values in ways.items():
        tags = way_values.get("tags", {})
        lift = {
            "id": way_id,
            "nodes": way_values.get("nodes"),
            "name": tags.get("name"),
        }

        # Check Validity
        if excluded_tags.intersection(tags):
            continue

        if "aerialway" not in tags:
            continue
        lift_type = tags.get("aerialway")

        if lift_type in invalid_types:
            continue

        lift["lift_type"] = lift_type

        occupancy = tags.get("aerialway:occupancy")
        if occupancy:
            occupancy = int(occupancy)
        lift["occupancy"] = occupancy
        capacity = tags.get("aerialway:capacity")
        if capacity:
            capacity = int(capacity)
        # if hourly capacity is unrealisticly low,
        # assume that it is mixed up with occupancy
        if capacity and capacity < 150:
            lift["occupancy"] = capacity
            capacity = None
        lift["capacity"] = capacity

        if (
            tags.get("aerialway:detatchable") == "yes"
            or "express" in lift["name"].lower()
        ):
            lift["detatchable"] = True
        else:
            lift["detatchable"] = False

        if tags.get("aerialway:bubble") == "yes":
            lift["bubble"] = True
        else:
            lift["bubble"] = False

        if tags.get("aerialway:heating") == "yes":
            lift["heating"] = True
        else:
            lift["heating"] = False

        lifts[way_id] = lift

    return {"lifts": lifts}
