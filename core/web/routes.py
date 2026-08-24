from dataclasses import dataclass
from urllib.parse import urlencode

from flask import Blueprint, current_app, render_template, request

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.mountain_query import list_mountains

web = Blueprint("web", __name__)


@dataclass
class NavigationLink:
    title: str
    page: str
    to: str


nav_links = [
    NavigationLink("About", "about", "/about"),
    NavigationLink("Search", "search", "/search"),
    NavigationLink("Explore Map", "explore_map", "/explore-map"),
    NavigationLink(
        "Mountain Rankings",
        "rankings",
        "/rankings?sort=difficulty&order=desc&region=usa",
    ),
    NavigationLink("Trail Rankings", "trail_rankings", "/trail-rankings?region=usa"),
    NavigationLink("Lift Rankings", "lift_rankings", "/lift-rankings?region=usa"),
    NavigationLink("Random Mountain", "random_map", "/random-mountain"),
]


@web.route("/")
def index():
    return render_template("index.jinja", nav_links=nav_links, active_page="index")


@web.route("/about")
def about():
    return render_template("about.jinja", nav_links=nav_links, active_page="about")


def _parse_state(value: str | None) -> State | None:
    if not value or value in ("None", "%%"):
        return None
    try:
        return State.from_name(value)
    except ValueError:
        pass
    try:
        return State(value)
    except ValueError:
        return None


@web.route("/search", methods=["GET", "POST"])
def search():
    q = (request.args.get("q") or "").strip()
    page = int(request.args.get("page") or 1)
    limit = int(request.args.get("limit") or 20)
    diffmin = float(request.args.get("diffmin") or 0)
    diffmax = float(request.args.get("diffmax") or 100)
    trailsmin = int(request.args.get("trailsmin") or 0)
    trailsmax = int(request.args.get("trailsmax") or 1000)
    sort = request.args.get("sort") or "name"
    order = request.args.get("order") or "asc"
    state = _parse_state(request.args.get("location"))

    offset = limit * (page - 1)

    db_path = current_app.config["DATABASE_PATH"]
    mountains, total_mountain_count = list_mountains(
        db_path=db_path,
        name_query=q or None,
        state=state,
        difficulty_min=diffmin,
        difficulty_max=diffmax,
        trail_count_min=trailsmin,
        trail_count_max=trailsmax,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )

    def _pagination_url(target_page: int) -> str:
        args = request.args.to_dict()
        args["page"] = str(target_page)
        return f"/search?{urlencode(args)}"

    pages = {}
    if total_mountain_count > limit and (limit * page) < total_mountain_count:
        pages["next"] = _pagination_url(page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url(page - 1)

    return render_template(
        "search.jinja",
        nav_links=nav_links,
        active_page="search",
        mountains=mountains,
        pages=pages,
    )


@web.route("/rankings")
def rankings():
    sort = request.args.get("sort") or "difficulty"
    order = request.args.get("order")
    region_param = request.args.get("region") or "usa"
    state_param = request.args.get("state")
    if state_param == "None":
        state_param = None

    sort_by = "beginner_friendliness" if sort == "beginner" else "difficulty"
    if order not in ("asc", "desc"):
        order = "desc"

    state = _parse_state(state_param)

    region = None
    if state is None and region_param != "usa":
        try:
            region = Region[region_param.upper()]
        except KeyError:
            region = None

    db_path = current_app.config["DATABASE_PATH"]
    mountains, _ = list_mountains(
        db_path=db_path,
        state=state,
        region=region,
        sort=sort_by,
        order=order,
    )

    return render_template(
        "rankings.jinja",
        nav_links=nav_links,
        active_page="rankings",
        mountains=mountains,
        sort=sort,
        order=order,
        region=region_param,
        state=state_param,
    )
