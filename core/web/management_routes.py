import os
from dataclasses import dataclass

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.blacklist import add_to_blacklist
from core.support.lift import Lift
from core.support.maps import create_map, create_thumbnail
from core.support.mountain import Mountain
from core.support.mountain_query import list_mountains
from core.support.trail import Trail
from core.support.utils import get_trail_difficulty
from core.web.routes import (
    NavigationLink,
    _build_geojson,
    _named_trails_and_lifts,
    _parse_state,
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
            mountain = Mountain.from_osm(osm_path, season_passes=[], url="")

            state_dir = os.path.join(OSM_DIR, mountain.state.value)
            os.makedirs(state_dir, exist_ok=True)
            final_osm_path = os.path.join(state_dir, f"{mountain.name}.osm")
            if os.path.abspath(osm_path) != os.path.abspath(final_osm_path):
                os.replace(osm_path, final_osm_path)

            db_path = current_app.config["DATABASE_PATH"]
            mountain.to_db(db_path)
            create_map(mountain)
            create_thumbnail(mountain)

            return redirect(
                url_for(
                    "web.interactive_map",
                    state=mountain.state.value,
                    name=mountain.name,
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
    trail_id), recomputing its difficulty the same way the old site's
    change_trail_stats did: reverse-engineer the weather modifier from the
    trail's current stored difficulty/steepest_30m/gladed/ungroomed, then
    reapply steepest_30m + that modifier + the new gladed/ungroomed bonus.
    """
    trail_id = request.args.get("trail_id")
    if not trail_id:
        return

    trail = mountain.trails.get(trail_id)
    if trail is None:
        return

    old_bonus = (5.5 if trail.gladed else 0) + (2.5 if trail.ungroomed else 0)
    weather_modifier = (trail.difficulty or 0) - (trail.steepest_30m or 0) - old_bonus

    trail.gladed = bool(request.args.get("gladed"))
    trail.ungroomed = bool(request.args.get("ungroomed"))
    trail.difficulty = get_trail_difficulty(
        trail.steepest_30m, trail.gladed, trail.ungroomed, weather_modifier
    )
    trail.to_db(db_path)


def _apply_delete(mountain: Mountain, db_path: str) -> None:
    """
    Deletes a trail or lift (identified by its OSM id) from the mountain,
    optionally blacklisting it so a future OSM refresh won't re-add it.
    """
    item_id = request.args.get("delete")
    if not item_id:
        return

    if item_id in mountain.trails:
        Trail.delete_from_db(item_id, db_path)
        del mountain.trails[item_id]
    elif item_id in mountain.lifts:
        Lift.delete_from_db(item_id, db_path)
        del mountain.lifts[item_id]
    else:
        return

    if request.args.get("blacklist"):
        add_to_blacklist(mountain.mountain_id, item_id, db_path)

    create_map(mountain)
    create_thumbnail(mountain)


@management_web.route("/management-edit-resort")
def management_edit_resort():
    db_path = current_app.config["DATABASE_PATH"]

    q = request.args.get("q")
    mountain = None
    if q:
        parts = q.split(",", 1)
        if len(parts) == 2:
            state = _parse_state(parts[1].strip())
            if isinstance(state, State):
                mountain = Mountain.from_name(parts[0].strip(), state, db_path)

    if mountain is not None:
        _apply_mountain_edits(mountain, db_path)
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
        trails, lifts = _named_trails_and_lifts(mountain)
        # debug_mode=True so popups always show OSM ids, matching the old
        # edit-resort page (public interactive-map only shows them behind
        # ?debug=true)
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
