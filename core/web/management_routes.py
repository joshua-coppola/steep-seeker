import os
from dataclasses import dataclass
from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from core.connectors.osm_api import OSM
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.blacklist import add_to_blacklist, is_blacklisted
from core.support.lift import Lift
from core.support.maps import create_map, create_thumbnail
from core.support.mountain import Mountain
from core.support.mountain_query import list_mountains
from core.support.trail import Trail
from core.support.utils import (
    get_bounding_box,
    get_trail_difficulty,
    weather_modifier_from_trail,
)
from core.web.routes import (
    NavigationLink,
    _build_geojson,
    _parse_state,
    _sorted_trails_and_lifts,
)
from core.web.routes import nav_links as public_nav_links

SEASON_PASS_FORM_FIELDS = {
    "epic": Season_Pass.EPIC,
    "ikon": Season_Pass.IKON,
    "mountain_collective": Season_Pass.MOUNTAIN_COLLECTIVE,
    "indy": Season_Pass.INDY,
    "cooper": Season_Pass.COOPER,
    "powder_alliance": Season_Pass.POWDER_ALLIANCE,
    "freedom": Season_Pass.FREEDOM,
    "power": Season_Pass.POWER,
}

management_web = Blueprint("management_web", __name__)

# the public nav plus a Management link -- kept separate from
# core.web.routes.nav_links so the public app (app_new.py) never shows a
# link into the admin pages, even though this blueprint can be registered
# alongside the public one (see management_app.py)
nav_links = [
    *public_nav_links,
    NavigationLink("Management", "management", "/management-add-resort"),
]


@dataclass
class ManagementLink:
    title: str
    to: str


management_links = [
    ManagementLink("Add Resort", "/management-add-resort"),
    ManagementLink("Edit Resort", "/management-edit-resort"),
]

OSM_DIR = "data/osm"
OSM_OLD_DIR = "data/osm-old"


def _available_osm_files(db_path: str) -> list[str]:
    """
    Returns "<state>/<name>" identifiers (without .osm) for every OSM file
    under data/osm/<state>/ that isn't already saved as a mountain in the
    DB, for the add-resort dropdown.
    """
    existing_mountains, _ = list_mountains(db_path=db_path)
    existing = {
        (mountain.state.value, mountain.name) for mountain in existing_mountains
    }

    available = []
    if not os.path.isdir(OSM_DIR):
        return available

    for state_dir in sorted(os.listdir(OSM_DIR)):
        state_path = os.path.join(OSM_DIR, state_dir)
        if not os.path.isdir(state_path):
            continue
        for filename in sorted(os.listdir(state_path)):
            if not filename.endswith(".osm"):
                continue
            name = filename[: -len(".osm")]
            if (state_dir, name) in existing:
                continue
            available.append(f"{state_dir}/{name}")

    return available


@management_web.route("/management-add-resort", methods=["GET", "POST"])
def management_add_resort():
    if request.method == "POST":
        osm_path = None

        file = request.files.get("file")
        if file and file.filename and file.filename.endswith(".osm"):
            # saved flat for now; moved into data/osm/<state>/ below once
            # the file's own state is known, matching how every other
            # resort's OSM file is organized
            osm_path = os.path.join(OSM_DIR, file.filename)
            file.save(osm_path)
        else:
            selection = request.form.get("q")
            if selection and selection != "none":
                osm_path = os.path.join(OSM_DIR, f"{selection}.osm")

        if osm_path:
            db_path = current_app.config["DATABASE_PATH"]
            mountain = Mountain.from_osm(
                osm_path, season_passes=[], url="", db_path=db_path
            )

            state_dir = os.path.join(OSM_DIR, mountain.state.value)
            os.makedirs(state_dir, exist_ok=True)
            final_osm_path = os.path.join(state_dir, f"{mountain.name}.osm")
            if os.path.abspath(osm_path) != os.path.abspath(final_osm_path):
                os.replace(osm_path, final_osm_path)

            mountain.to_db(db_path)
            create_map(mountain)
            create_thumbnail(mountain)

            return redirect(
                url_for(
                    "management_web.management_edit_resort",
                    q=f"{mountain.name}, {mountain.state.value}",
                )
            )

    return render_template(
        "management-add-resort.jinja",
        management_links=management_links,
        active_page="Add Resort",
        resorts=_available_osm_files(current_app.config["DATABASE_PATH"]),
    )


def _rename_resort_files(state: str, old_name: str, new_name: str) -> None:
    """
    Moves a resort's OSM source file and thumbnail to match a new name.
    The map SVG isn't moved -- it's regenerated instead, since it renders
    the resort's name as its title (the thumbnail doesn't, so a plain move
    is enough for it).
    """
    osm_old = os.path.join(OSM_DIR, state, f"{old_name}.osm")
    osm_new = os.path.join(OSM_DIR, state, f"{new_name}.osm")
    if os.path.exists(osm_old):
        os.rename(osm_old, osm_new)

    thumbnail_old = os.path.join("static/thumbnails", state, f"{old_name}.svg")
    thumbnail_new = os.path.join("static/thumbnails", state, f"{new_name}.svg")
    if os.path.exists(thumbnail_old):
        os.rename(thumbnail_old, thumbnail_new)


def _apply_mountain_edits(mountain: Mountain, db_path: str) -> None:
    """
    Applies whichever of the season-passes/URL/rename edits were submitted
    with this request to the given (already-loaded) mountain, persisting
    each change immediately.
    """
    if request.args.get("update_passes"):
        mountain.season_passes = [
            season_pass
            for field, season_pass in SEASON_PASS_FORM_FIELDS.items()
            if request.args.get(field)
        ]
        mountain.to_db(db_path)

    new_url = request.args.get("url")
    if new_url:
        mountain.url = new_url
        mountain.to_db(db_path)

    new_name = request.args.get("rename")
    if new_name and new_name != mountain.name:
        _rename_resort_files(mountain.state.value, mountain.name, new_name)
        mountain.name = new_name
        mountain.to_db(db_path)
        create_map(mountain)


def _apply_trail_edit(mountain: Mountain, db_path: str) -> None:
    """
    Applies a gladed/ungroomed tag edit to one trail (identified by
    trail_id), recomputing its difficulty by reverse-engineering the weather
    modifier from the trail's current stored
    difficulty/steepest_30m/gladed/ungroomed,
    then reapply steepest_30m + that modifier + the new gladed/ungroomed bonus.
    """
    trail_id = request.args.get("trail_id")
    if not trail_id:
        return

    trail = mountain.trails.get(trail_id)
    if trail is None:
        return

    weather_modifier = weather_modifier_from_trail(trail)

    trail.gladed = bool(request.args.get("gladed"))
    trail.ungroomed = bool(request.args.get("ungroomed"))
    trail.difficulty = get_trail_difficulty(
        trail.steepest_30m, trail.gladed, trail.ungroomed, weather_modifier
    )
    trail.to_db(db_path)

    mountain.recalculate_stats()
    mountain.update_stats_in_db(db_path)


def _apply_rotate(mountain: Mountain, db_path: str) -> None:
    """
    Rotates the mountain's map orientation a quarter turn clockwise or
    counter-clockwise
    """
    if request.args.get("rotate"):
        mountain.rotate_clockwise()
    elif request.args.get("rotate_ccw"):
        mountain.rotate_counterclockwise()
    else:
        return

    mountain.to_db(db_path)
    create_map(mountain)
    create_thumbnail(mountain)


def _rebuild_from_osm_file(
    mountain: Mountain,
    osm_path: str,
    db_path: str,
    ignore_areas: bool = False,
    blacklist_areas: bool = False,
) -> Mountain | None:
    """
    Re-parses the given local OSM file into a fresh trail/lift set for
    the mountain (reusing its existing mountain_id so the reload attaches
    to the same DB row), drops anything blacklisted so a previously
    deleted item doesn't come back. Replaces the mountain's trails/lifts
    in the DB with this new set.

    When "ignore_areas" is set, glade/bowl (area) trails are dropped from
    the rebuild; "blacklist_areas" additionally blacklists those ids so
    they stay gone on future refreshes even without "ignore_areas".

    Returns None (leaving the DB untouched) if the file is missing or the
    parse comes back with zero trails, since rebuilding from an empty or
    failed parse would wipe out real data.
    """
    if not os.path.exists(osm_path):
        return None

    refreshed = Mountain.from_osm(
        osm_path,
        season_passes=mountain.season_passes,
        url=mountain.url,
        mountain_id=mountain.mountain_id,
        db_path=db_path,
    )

    # keep the map orientation the mountain already had -- it's only
    # meant to change when an admin explicitly rotates the map, not as a
    # side effect of a refresh re-deriving it from (possibly shifted) OSM
    # geometry
    refreshed.direction = mountain.direction

    if ignore_areas:
        area_trail_ids = [
            trail_id for trail_id, trail in refreshed.trails.items() if trail.area
        ]
        for trail_id in area_trail_ids:
            if blacklist_areas:
                add_to_blacklist(mountain.mountain_id, trail_id, db_path)
            del refreshed.trails[trail_id]

    if not refreshed.trails:
        return None

    refreshed.trails = {
        trail_id: trail
        for trail_id, trail in refreshed.trails.items()
        if not is_blacklisted(mountain.mountain_id, trail_id, db_path)
    }
    refreshed.lifts = {
        lift_id: lift
        for lift_id, lift in refreshed.lifts.items()
        if not is_blacklisted(mountain.mountain_id, lift_id, db_path)
    }

    refreshed.recalculate_stats()

    Mountain.clear_trails_and_lifts(mountain.mountain_id, db_path)
    refreshed.to_db(db_path)

    return refreshed


def _archive_osm_file(osm_path: str) -> None:
    """
    Moves an existing OSM file aside into data/osm-old/<state>/, named
    with its last-modified date, before it gets overwritten by a fresh
    extract. A no-op if there's no existing file to archive (e.g. the
    very first full refresh).
    """
    if not os.path.exists(osm_path):
        return

    state_dir, filename = os.path.split(osm_path)
    state = os.path.basename(state_dir)
    old_date = datetime.fromtimestamp(
        os.stat(osm_path).st_mtime, tz=timezone.utc
    ).date()

    archive_dir = os.path.join(OSM_OLD_DIR, state)
    os.makedirs(archive_dir, exist_ok=True)
    os.replace(osm_path, os.path.join(archive_dir, f"{old_date} {filename}"))


def _full_refresh(mountain: Mountain, db_path: str) -> Mountain | None:
    """
    Fetches a brand-new OSM extract from Overpass for a bounding box
    covering the mountain's current trails/lifts (padded outward by
    "size_increase", for resorts that have grown past their original
    boundary), archives the existing local OSM file and replaces it with
    the new extract, then rebuilds trails/lifts/stats from that new file
    the same way a stats refresh does -- "ignore_areas" and
    "blacklist_areas" apply here too.

    Returns None (leaving the DB and local file untouched) if the fetch
    fails.
    """
    size_increase = float(request.args.get("size_increase") or 0)
    geometries = [trail.geometry for trail in mountain.trails.values()] + [
        lift.geometry for lift in mountain.lifts.values()
    ]
    bbox = get_bounding_box(geometries, padding=size_increase)

    extract = OSM().get(bbox)
    if extract is None:
        return None

    osm_path = os.path.join(OSM_DIR, mountain.state.value, f"{mountain.name}.osm")
    _archive_osm_file(osm_path)
    os.makedirs(os.path.dirname(osm_path), exist_ok=True)
    with open(osm_path, "wb") as f:
        f.write(extract)

    ignore_areas = bool(request.args.get("ignore_areas"))
    blacklist_areas = bool(request.args.get("blacklist_areas"))
    return _rebuild_from_osm_file(
        mountain, osm_path, db_path, ignore_areas, blacklist_areas
    )


def _apply_refresh(mountain: Mountain, db_path: str) -> Mountain:
    """
    Applies whichever refresh variant(s) were submitted, returning the
    (possibly reloaded) mountain to keep rendering with. full_refresh
    takes priority over stats_refresh if both are somehow submitted at
    once.

    The map/thumbnail are only regenerated when a refresh actually
    changed something: map_refresh always regenerates it (there's
    nothing for it to fail), but a stats/full refresh that couldn't run
    (missing file, failed fetch, empty parse) leaves the existing map
    alone rather than re-rendering unchanged data.
    """
    refreshed = None

    if request.args.get("full_refresh"):
        refreshed = _full_refresh(mountain, db_path)
    elif request.args.get("stats_refresh"):
        osm_path = os.path.join(OSM_DIR, mountain.state.value, f"{mountain.name}.osm")
        ignore_areas = bool(request.args.get("ignore_areas"))
        blacklist_areas = bool(request.args.get("blacklist_areas"))
        refreshed = _rebuild_from_osm_file(
            mountain, osm_path, db_path, ignore_areas, blacklist_areas
        )

    if refreshed is not None:
        mountain = refreshed
        create_map(mountain)
        create_thumbnail(mountain)

    if request.args.get("map_refresh"):
        create_map(mountain)
        create_thumbnail(mountain)

    return mountain


def _delete_resort(mountain: Mountain, db_path: str) -> None:
    """
    Permanently deletes a resort: its DB rows (mountain, trails, lifts,
    blacklist entries) and its generated map/thumbnail SVGs. The source
    OSM file is only removed when "delete_osm" is checked.
    """
    state = mountain.state.value
    name = mountain.name

    Mountain.delete_from_db(mountain.mountain_id, db_path)

    map_path = os.path.join("static/maps", state, f"{name}.svg")
    if os.path.exists(map_path):
        os.remove(map_path)

    thumbnail_path = os.path.join("static/thumbnails", state, f"{name}.svg")
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)

    if request.args.get("delete_osm"):
        osm_path = os.path.join(OSM_DIR, state, f"{name}.osm")
        if os.path.exists(osm_path):
            os.remove(osm_path)


def _delete_item(
    mountain: Mountain, item_id: str, db_path: str, blacklist: bool
) -> bool:
    """
    Removes one trail or lift (identified by its OSM id) from the mountain
    and the DB, optionally blacklisting it so a future refresh won't
    re-add it. Returns True if something was deleted.

    Does not regenerate the map/thumbnail -- callers do that once after
    all deletions so a bulk delete only pays that cost a single time.
    """
    if item_id in mountain.trails:
        Trail.delete_from_db(item_id, db_path)
        del mountain.trails[item_id]
        mountain.recalculate_stats()
        mountain.update_stats_in_db(db_path)
    elif item_id in mountain.lifts:
        Lift.delete_from_db(item_id, db_path)
        del mountain.lifts[item_id]
    else:
        return False

    if blacklist:
        add_to_blacklist(mountain.mountain_id, item_id, db_path)

    return True


def _apply_delete(mountain: Mountain, db_path: str) -> None:
    """
    Deletes a trail or lift (identified by its OSM id) from the mountain,
    optionally blacklisting it so a future refresh won't re-add it.
    """
    item_id = request.args.get("delete")
    if not item_id:
        return

    if _delete_item(mountain, item_id, db_path, bool(request.args.get("blacklist"))):
        create_map(mountain)
        create_thumbnail(mountain)


def _load_mountain(q: str | None, db_path: str) -> Mountain | None:
    """
    Resolves the "<name>, <state>" the edit page's resort selector uses
    into a Mountain, or None if it's missing/unparseable/unknown.
    """
    if not q:
        return None

    parts = q.split(",", 1)
    if len(parts) != 2:
        return None

    state = _parse_state(parts[1].strip())
    if not isinstance(state, State):
        return None

    return Mountain.from_name(parts[0].strip(), state, db_path)


@management_web.route("/management-edit-resort/bulk-delete", methods=["POST"])
def management_bulk_delete():
    """
    Deletes every trail/lift id in the "ids" form field in one shot,
    regenerating the map/thumbnail only once at the end, then returns to
    the edit page. Backs the map's delete-mode (see interactive-map.js).
    """
    db_path = current_app.config["DATABASE_PATH"]
    q = request.form.get("q")
    mountain = _load_mountain(q, db_path)

    if mountain is not None:
        blacklist = bool(request.form.get("blacklist"))
        deleted = False
        for item_id in request.form.getlist("ids"):
            if _delete_item(mountain, item_id, db_path, blacklist):
                deleted = True

        if deleted:
            create_map(mountain)
            create_thumbnail(mountain)

    return redirect(url_for("management_web.management_edit_resort", q=q))


@management_web.route("/management-edit-resort")
def management_edit_resort():
    db_path = current_app.config["DATABASE_PATH"]

    mountain = _load_mountain(request.args.get("q"), db_path)

    if mountain is not None:
        if request.args.get("delete_resort") == "DELETE":
            _delete_resort(mountain, db_path)
            mountain = None
        else:
            mountain = _apply_refresh(mountain, db_path)
            _apply_mountain_edits(mountain, db_path)
            _apply_rotate(mountain, db_path)
            _apply_trail_edit(mountain, db_path)
            _apply_delete(mountain, db_path)

    all_mountains, _ = list_mountains(db_path=db_path)
    resorts = sorted(f"{m.name}, {m.state.value}" for m in all_mountains)

    mountain_index = -1
    if mountain is not None:
        mountain_label = f"{mountain.name}, {mountain.state.value}"
        if mountain_label in resorts:
            mountain_index = resorts.index(mountain_label)

    next_mountain = ""
    if resorts:
        if mountain_index == len(resorts) - 1:
            mountain_index = -1
        next_mountain = resorts[mountain_index + 1]

    trails, lifts = [], []
    geojson = {
        "type": "FeatureCollection",
        "features": [],
        "properties": {"summary": "elevation"},
    }
    if mountain is not None:
        trails, lifts = _sorted_trails_and_lifts(mountain)
        # debug_mode=True so popups always show OSM ids
        geojson = _build_geojson(
            mountain, trails, lifts, debug_mode=True, editable=True
        )

    season_pass_values = set()
    if mountain is not None:
        season_pass_values = {
            season_pass.value for season_pass in mountain.season_passes
        }

    return render_template(
        "management-edit-resort.jinja",
        management_links=management_links,
        active_page="Edit Resort",
        resorts=resorts,
        mountain=mountain,
        season_pass_values=season_pass_values,
        geojson=geojson,
        next_mountain=next_mountain,
        trails=trails,
        lifts=lifts,
    )
