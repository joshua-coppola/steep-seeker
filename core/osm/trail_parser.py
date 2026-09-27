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

        # Skip irrelevant features. A dual-tagged bike/ski trail
        # (mtb:scale:imba alongside piste:type) is only trusted as a real
        # ski trail if it also carries piste:difficulty or piste:name --
        # otherwise the piste:type is assumed incidental to a trail that's
        # really just mapped for mountain biking.
        is_untrusted_bike_trail = "mtb:scale:imba" in tags and not (
            tags.get("piste:difficulty") or tags.get("piste:name")
        )
        if (
            is_untrusted_bike_trail
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

        # Hazardous is never OSM-derived -- only set manually from the
        # management edit-resort popup, so every freshly parsed trail starts
        # unflagged
        trail["hazardous"] = False

        # multi_route is never OSM-derived either -- it's set by
        # OSMProcessor._merge_multi_route_clusters when a branch/rejoin is
        # detected across several ways, so every freshly parsed (single-way)
        # trail starts False
        trail["multi_route"] = False

        # if both gladed and ungroomed, only keep gladed
        if trail["gladed"] and trail["ungroomed"]:
            trail["ungroomed"] = False

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


def identify_hikes(ways, relations):
    """
    Accepts a dict of ways and relations and identifies hike-to access
    routes (piste:type=hike -- bootpacks, ridge walks, backcountry gate
    access, etc). Returns a dict containing the valid hikes and relations.

    Hikes are deliberately shaped like lift dicts (id, nodes, name,
    lift_type, occupancy/capacity/detachable/bubble/heating), not trail
    dicts -- they carry no difficulty rating or ski-specific metadata, and
    are assembled into Lift objects (lift_type="hike") alongside real lifts.
    """
    hikes = {}

    excluded_tags = {"disused", "abandoned", "proposed"}
    invalid_name_substrings = ["closed"]

    for way_id, way_values in ways.items():
        tags = way_values.get("tags", {})

        if tags.get("piste:type") != "hike":
            continue

        if excluded_tags.intersection(tags):
            continue

        name = tags.get("piste:name") or tags.get("name") or ""
        if name and any(substr in name.lower() for substr in invalid_name_substrings):
            continue

        hikes[way_id] = {
            "id": way_id,
            "nodes": way_values.get("nodes"),
            "name": name,
            "lift_type": "hike",
            "occupancy": None,
            "capacity": None,
            "detachable": None,
            "bubble": None,
            "heating": None,
        }

    hike_relations = {}
    for relation_id, relation_values in relations.items():
        tags = relation_values.get("tags", {})

        if tags.get("piste:type") != "hike":
            continue

        hike_relations[relation_id] = {
            "id": relation_id,
            "members": relation_values.get("members"),
            "type": tags.get("type"),
        }

    return {"hikes": hikes, "relations": hike_relations}


def identify_lifts(ways):
    """
    Accepts a dict of ways and identifies the valid trails.
    Returns a dict containing the valid lifts.
    """
    lifts = {}

    invalid_types = {
        "goods",
        "station",
        "zip_line",
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
            "name": tags.get("name") or "",
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

        # OSM tag values are free-form; a non-integer ("4;6", "quad", ...)
        # becomes None rather than raising and aborting the mountain ingest
        occupancy = tags.get("aerialway:occupancy")
        lift["occupancy"] = (
            int(occupancy) if occupancy and occupancy.isdigit() else None
        )
        capacity = tags.get("aerialway:capacity")
        capacity = int(capacity) if capacity and capacity.isdigit() else None
        # if hourly capacity is unrealisticly low,
        # assume that it is mixed up with occupancy
        if capacity and capacity < 150:
            lift["occupancy"] = capacity
            capacity = None
        lift["capacity"] = capacity

        if tags.get("aerialway:detachable") == "yes" or (
            lift["name"] and "express" in lift["name"].lower()
        ):
            lift["detachable"] = True
        else:
            lift["detachable"] = False

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
