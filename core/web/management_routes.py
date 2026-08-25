import os
from dataclasses import dataclass

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from core.support.maps import create_map, create_thumbnail
from core.support.mountain import Mountain
from core.support.mountain_query import list_mountains
from core.web.routes import NavigationLink
from core.web.routes import nav_links as public_nav_links

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
