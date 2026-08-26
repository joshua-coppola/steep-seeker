import random
from dataclasses import dataclass
from math import atan2, degrees
from urllib.parse import urlencode

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.lift_query import list_lifts
from core.support.mountain import Mountain
from core.support.mountain_query import list_mountains
from core.support.trail_query import list_trails
from core.support.utils import build_elevation_profile, round_degrees, trail_color

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
    return render_template("index.jinja", active_page="index")


@web.route("/about")
def about():
    return render_template("about.jinja", active_page="about")


@web.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.jinja")


@web.route("/random-mountain")
def random_mountain():
    db_path = current_app.config["DATABASE_PATH"]
    mountains, _ = list_mountains(db_path=db_path)
    mountain = random.choice(mountains)

    return redirect(
        url_for("web.interactive_map", state=mountain.state.value, name=mountain.name)
    )


class _InvalidState:
    """Sentinel: a state value was given but doesn't parse to a real State."""


_INVALID_STATE = _InvalidState()


def _parse_state(value: str | None) -> State | None | _InvalidState:
    """
    Returns a State, None (no location given), or _INVALID_STATE (a
    location was given but isn't a real state). Callers filtering by the
    result must treat _INVALID_STATE as "matches nothing", not "no
    filter".
    """
    if not value or value in ("None", "%%"):
        return None
    try:
        return State.from_name(value)
    except ValueError:
        pass
    try:
        return State(value)
    except ValueError:
        return _INVALID_STATE


def _parse_region(region_param: str, state: State | None) -> Region | None:
    # state, when given, takes priority over region
    if state is not None or region_param == "usa":
        return None
    try:
        return Region[region_param.upper()]
    except KeyError:
        return None


@web.route("/search", methods=["GET", "POST"])
def search():
    q = (request.args.get("q") or "").strip()
    page = int(request.args.get("page") or 1)
    limit = int(request.args.get("limit") or 20)
    diffmin = float(request.args.get("diffmin") or 0)
    diffmax = float(request.args.get("diffmax") or 100)
    # search.js sends "Infinity" for trailsmax when its slider's upper
    # handle is maxed out (meaning "no limit"); float() parses that
    # natively, unlike int()
    trailsmin = float(request.args.get("trailsmin") or 0)
    trailsmax = float(request.args.get("trailsmax") or 1000)
    sort = request.args.get("sort") or "name"
    order = request.args.get("order") or "asc"
    state = _parse_state(request.args.get("location"))

    offset = limit * (page - 1)

    db_path = current_app.config["DATABASE_PATH"]
    if state is _INVALID_STATE:
        mountains, total_mountain_count = [], 0
    else:
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

    db_path = current_app.config["DATABASE_PATH"]
    if state is _INVALID_STATE:
        mountains = []
    else:
        region = _parse_region(region_param, state)
        mountains, _ = list_mountains(
            db_path=db_path,
            state=state,
            region=region,
            sort=sort_by,
            order=order,
        )

    return render_template(
        "rankings.jinja",
        active_page="rankings",
        mountains=mountains,
        sort=sort,
        order=order,
        region=region_param,
        state=state_param,
    )


@web.route("/trail-rankings")
def trail_rankings():
    region_param = request.args.get("region") or "usa"
    state_param = request.args.get("state")
    if state_param == "None":
        state_param = None
    page = int(request.args.get("page") or 1)
    limit = min(int(request.args.get("limit") or 50), 200)
    sort_by = request.args.get("sort") or "difficulty"

    offset = limit * (page - 1)

    state = _parse_state(state_param)

    db_path = current_app.config["DATABASE_PATH"]
    if state is _INVALID_STATE:
        trails, total_trail_count = [], 0
    else:
        region = _parse_region(region_param, state)
        trails, total_trail_count = list_trails(
            db_path=db_path,
            state=state,
            region=region,
            sort=sort_by,
            limit=limit,
            offset=offset,
        )

    def _pagination_url(target_page: int) -> str:
        args = request.args.to_dict()
        args["page"] = str(target_page)
        return f"/trail-rankings?{urlencode(args)}"

    pages = {"offset": offset}
    if total_trail_count > limit and (limit * page) < total_trail_count:
        pages["next"] = _pagination_url(page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url(page - 1)
    first_args = {"region": region_param, "limit": limit}
    if state_param:
        first_args["state"] = state_param
    pages["first"] = f"/trail-rankings?{urlencode(first_args)}"

    return render_template(
        "trail_rankings.jinja",
        active_page="trail_rankings",
        trails=trails,
        region=region_param,
        state=state_param,
        pages=pages,
        sort_by=sort_by,
    )


@web.route("/lift-rankings")
def lift_rankings():
    region_param = request.args.get("region") or "usa"
    state_param = request.args.get("state")
    if state_param == "None":
        state_param = None
    page = int(request.args.get("page") or 1)
    limit = min(int(request.args.get("limit") or 50), 200)
    sort_by = request.args.get("sort") or "vertical"

    offset = limit * (page - 1)

    state = _parse_state(state_param)

    db_path = current_app.config["DATABASE_PATH"]
    if state is _INVALID_STATE:
        lifts, total_lift_count = [], 0
    else:
        region = _parse_region(region_param, state)
        lifts, total_lift_count = list_lifts(
            db_path=db_path,
            state=state,
            region=region,
            sort=sort_by,
            limit=limit,
            offset=offset,
        )

    def _pagination_url(target_page: int) -> str:
        args = request.args.to_dict()
        args["page"] = str(target_page)
        return f"/lift-rankings?{urlencode(args)}"

    pages = {"offset": offset}
    if total_lift_count > limit and (limit * page) < total_lift_count:
        pages["next"] = _pagination_url(page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url(page - 1)
    first_args = {"region": region_param, "limit": limit}
    if state_param:
        first_args["state"] = state_param
    pages["first"] = f"/lift-rankings?{urlencode(first_args)}"

    return render_template(
        "lift_rankings.jinja",
        active_page="lift_rankings",
        lifts=lifts,
        region=region_param,
        state=state_param,
        pages=pages,
        sort_by=sort_by,
    )


def _orientation(
    lon_points: list[float], lat_points: list[float], is_area: bool, direction: str
) -> int:
    """
    Picks which side of a trail/lift line its name label should be
    written on (0 or 180 degrees), based on the line's rough bearing at
    its midpoint and which way the mountain map itself is rotated
    (mountain.direction). Area trails' polygon outlines don't have a
    single meaningful direction, so they're never flipped.
    """
    midpoint = int(len(lon_points) / 2)
    dx = (
        lon_points[max(midpoint - 5, 0)]
        - lon_points[min(midpoint + 5, (midpoint * 2) - 1)]
    )
    dy = (
        lat_points[max(midpoint - 5, 0)]
        - lat_points[min(midpoint + 5, (midpoint * 2) - 1)]
    )
    ang = degrees(atan2(dy, dx))
    orientation = 0
    if abs(ang) < 90 and not is_area and direction == "s":
        orientation = 180
    if abs(ang) > 90 and not is_area and direction == "n":
        orientation = 180
    if ang > 0 and not is_area and direction == "w":
        orientation = 180
    if ang < 0 and not is_area and direction == "e":
        orientation = 180

    return orientation


def _delete_form_html(edit_query: str, item_id: str) -> str:
    """
    Delete/blacklist form appended to a trail or lift's popup when the
    management edit page is building it -- shared since it's identical
    for both (only the id value differs).
    """
    return (
        '<form id="delete" class="search-form">'
        f'<input type="hidden" name="q" value="{edit_query}">'
        f'<input type="hidden" name="delete" value="{item_id}">'
        '<span class="checkbox-group">'
        '<input type="checkbox" id="blacklist" name="blacklist" value=True>'
        '<label for="blacklist">Blacklist</label>'
        "</span>"
        '<input class="button-cta" id="delete_submit" type="submit" value="Delete" /></form>'
    )


def _trail_features(
    trail, direction: str, debug_mode: bool, edit_query: str | None = None
) -> list[dict]:
    """
    Builds the GeoJSON feature(s) for one trail. A line trail is a single
    LineString feature. An area trail (glade/bowl, sampled as a polygon)
    is its boundary Polygon feature plus -- when a route has been computed
    for it -- a second, faint/non-interactive LineString feature (styled in
    interactive-map.js) carrying that route's elevation profile. The polygon's
    own properties carry the route's profile too (as routeCoordinates), so
    interactive-map.js can show a real heightgraph when the polygon
    itself is clicked.

    edit_query, when given (the "<name>, <state>" the management edit
    page's mountain selector uses), appends a gladed/ungroomed tag-edit
    form to the popup: only management_routes.py's edit page passes
    this; the public interactive-map never does.
    """
    if trail.area:
        coords = list(trail.geometry.exterior.coords)
        profile = build_elevation_profile(coords)
        geometry = {"type": "Polygon", "coordinates": [profile + [profile[0]]]}
    else:
        coords = list(trail.geometry.coords)
        profile = build_elevation_profile(coords)
        geometry = {"type": "LineString", "coordinates": profile}

    lon_points = [c[0] for c in coords]
    lat_points = [c[1] for c in coords]
    orientation = _orientation(lon_points, lat_points, trail.area, direction)

    gladed_icon = '<i class="icon gladed"></i>' if trail.gladed else ""
    ungroomed_icon = '<i class="icon ungroomed"></i>' if trail.ungroomed else ""
    popup_content = f"<h3>{trail.name}{gladed_icon}{ungroomed_icon}</h3>"
    popup_content += (
        f"<p>Rating: {trail.difficulty}"
        f'<span class="icon difficulty-{trail_color(trail.difficulty)}"></span></p>'
    )
    popup_content += (
        f"<p>Length: {trail.length_feet()} ft</p>"
        f"<p>Vertical Drop: {trail.vertical_feet()} ft</p>"
    )
    for window in ("30m", "50m", "100m", "200m", "500m", "1000m"):
        value = getattr(trail, f"steepest_{window}")
        if value:
            popup_content += (
                f"<p>{window} Pitch: {value}\N{DEGREE SIGN}"
                f'<span class="icon difficulty-{trail_color(value)}"></span></p>'
            )
    if debug_mode:
        popup_content += f"<p>Trail ID: {trail.trail_id}</p>"
    if edit_query is not None:
        gladed_checked = "checked" if trail.gladed else ""
        ungroomed_checked = "checked" if trail.ungroomed else ""
        popup_content += (
            '<form id="update_tags" class="search-form">'
            f'<input type="hidden" name="q" value="{edit_query}">'
            f'<input type="hidden" name="trail_id" value="{trail.trail_id}">'
            '<span class="checkbox-group">'
            f'<input type="checkbox" id="gladed" name="gladed" value=True {gladed_checked}>'
            '<label for="gladed">Gladed</label>'
            "</span>"
            '<span class="checkbox-group">'
            f'<input type="checkbox" id="ungroomed" name="ungroomed" value=True {ungroomed_checked}>'
            '<label for="ungroomed">Ungroomed</label>'
            "</span>"
            '<input class="button-cta" id="update_tags_submit" type="submit" value="Update" /></form>'
        )
        popup_content += _delete_form_html(edit_query, trail.trail_id)

    properties = {
        "popupContent": popup_content,
        # name is the trail's identity (used for the elevation-profile
        # title regardless of which feature was clicked); label is
        # specifically the text drawn along the map -- the two diverge for
        # an area trail, whose label moves onto its route line below
        "name": trail.name,
        "label": trail.name,
        "orientation": orientation,
        "color": trail_color(trail.difficulty),
        "gladed": str(trail.gladed),
        "difficulty_modifier": (trail.difficulty or 0) - (trail.steepest_30m or 0),
    }

    features = [{"type": "Feature", "properties": properties, "geometry": geometry}]

    if trail.area and trail.route is not None:
        route_coords = list(trail.route.coords)
        route_profile = build_elevation_profile(route_coords)
        properties["routeCoordinates"] = route_profile

        # An irregular polygon border reads badly as a text path, so the
        # name label moves onto the route line instead -- the route has
        # real start-to-end direction, so its orientation is computed like
        # a normal line trail's rather than an area trail's fixed 0.
        del properties["label"]
        route_lon_points = [c[0] for c in route_coords]
        route_lat_points = [c[1] for c in route_coords]
        route_orientation = _orientation(
            route_lon_points, route_lat_points, False, direction
        )

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "isRoute": True,
                    "color": properties["color"],
                    "label": trail.name,
                    "orientation": route_orientation,
                },
                "geometry": {"type": "LineString", "coordinates": route_profile},
            }
        )

    return features


def _lift_feature(
    lift,
    direction: str,
    weather_modifier: float,
    debug_mode: bool,
    edit_query: str | None = None,
) -> dict:
    coords = list(lift.geometry.coords)
    profile = build_elevation_profile(coords)
    lon_points = [c[0] for c in coords]
    lat_points = [c[1] for c in coords]
    orientation = _orientation(lon_points, lat_points, False, direction)

    popup_content = f"<h3>{lift.name}</h3>"
    if lift.occupancy:
        if lift.occupancy <= 4:
            popup_content += (
                "<p>" + '<span class="icon person"></span>' * lift.occupancy + "</p>"
            )
        else:
            popup_content += (
                f'<p class="occupancy">{lift.occupancy}'
                '<span class="small-spacer"></span>'
                '<span class="icon person"></span></p>'
            )
    popup_content += f"<p>Length: {lift.length_feet()} ft</p>"
    popup_content += f"<p>Vertical Rise: {lift.vertical_feet()} ft</p>"
    popup_content += f"<p>Average Pitch: {round_degrees(lift.average_slope)}°</p>"
    if lift.bubble:
        popup_content += "<p>&#x2705; Bubble</p>"
    if lift.heating:
        popup_content += "<p>&#x2705; Heated</p>"
    if debug_mode:
        popup_content += f"<p>Lift ID: {lift.lift_id}</p>"
    if edit_query is not None:
        popup_content += _delete_form_html(edit_query, lift.lift_id)

    return {
        "type": "Feature",
        "properties": {
            "popupContent": popup_content,
            "name": lift.name,
            "label": lift.name,
            "orientation": orientation,
            "color": "grey",
            "difficulty_modifier": weather_modifier,
        },
        "geometry": {"type": "LineString", "coordinates": profile},
    }


@web.route("/explore-map")
def explore_map():
    db_path = current_app.config["DATABASE_PATH"]
    mountains, _ = list_mountains(db_path=db_path)

    features = []
    for mountain in mountains:
        difficulty_color = trail_color(mountain.difficulty)

        beginner_color = "gold"
        if mountain.beginner_friendliness > -17:
            beginner_color = "red"
        if mountain.beginner_friendliness > -6:
            beginner_color = "black"
        if mountain.beginner_friendliness > 3:
            beginner_color = "royalblue"
        if mountain.beginner_friendliness > 12:
            beginner_color = "green"

        popup_content = (
            f'<h3><a href="/interactive-map/{mountain.state.value}/{mountain.name}">'
            f"{mountain.name}</a></h3>"
        )
        for season_pass in mountain.season_passes:
            popup_content += (
                f'<img src="icons/{season_pass.value}.png" class="pass-icon"/>'
            )
        popup_content += (
            f"<p>Vertical: {mountain.vertical} ft</p>"
            f'<p>Difficulty: {mountain.difficulty}<span class="icon difficulty-{difficulty_color}"></span></p>'
            f'<p>Beginner Friendliness: {mountain.beginner_friendliness}<span class="icon difficulty-{beginner_color}"></span></p>'
        )

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": mountain.name,
                    "state": mountain.state.value,
                    "trail_count": mountain.trail_count,
                    "lift_count": mountain.lift_count,
                    "vertical": mountain.vertical,
                    "difficulty": mountain.difficulty,
                    "beginner_friendliness": mountain.beginner_friendliness,
                    "size": mountain.vertical ** (1 / 3) / 20,
                    "popupContent": popup_content,
                    "icon": f"icons/mountain_{difficulty_color}.png",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [mountain.coordinates.x, mountain.coordinates.y],
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}

    return render_template(
        "explore_map.jinja",
        active_page="explore_map",
        geojson=geojson,
    )


def _load_mountain_or_404(state: str, name: str, db_path: str) -> Mountain:
    state_enum = _parse_state(state)
    if not isinstance(state_enum, State):
        abort(404)

    mountain = Mountain.from_name(name, state_enum, db_path)
    if mountain is None:
        abort(404)

    return mountain


def _sorted_trails_and_lifts(mountain: Mountain) -> tuple[list, list]:
    """
    Returns (trails, lifts): all of the mountain's trails sorted by
    difficulty descending, and all of its lifts -- including unnamed ones
    (e.g. connector segments), since those still need to be plotted on
    the map. Shared by /map and /interactive-map's sidebar + (for
    interactive-map) GeoJSON building.
    """
    trails = sorted(
        mountain.trails.values(),
        key=lambda t: t.difficulty if t.difficulty is not None else -1,
        reverse=True,
    )
    lifts = list(mountain.lifts.values())

    return trails, lifts


@web.route("/map/<string:state>/<string:name>")
def static_map(state, name):
    db_path = current_app.config["DATABASE_PATH"]
    mountain = _load_mountain_or_404(state, name, db_path)

    trails, lifts = _sorted_trails_and_lifts(mountain)

    return render_template(
        "map.jinja",
        active_page="map",
        mountain=mountain,
        trails=trails,
        lifts=lifts,
    )


def _weather_modifier(trails: list) -> float:
    """
    Recovers the mountain's weather modifier alone (stripping the
    gladed/ungroomed bonus baked into trails[0]'s difficulty), since
    lifts don't carry their own difficulty_modifier
    """
    if not trails:
        return 0

    first = trails[0]
    if first.difficulty is None or first.steepest_30m is None:
        return 0

    return (
        first.difficulty
        - first.steepest_30m
        - (5.5 if first.gladed else 0)
        - (2.5 if first.ungroomed else 0)
    )


def _build_geojson(
    mountain: Mountain,
    trails: list,
    lifts: list,
    debug_mode: bool,
    editable: bool = False,
) -> dict:
    weather_modifier = _weather_modifier(trails)
    edit_query = f"{mountain.name}, {mountain.state.value}" if editable else None

    features = []
    for trail in trails:
        features.extend(
            _trail_features(trail, mountain.direction, debug_mode, edit_query)
        )
    for lift in lifts:
        features.append(
            _lift_feature(
                lift, mountain.direction, weather_modifier, debug_mode, edit_query
            )
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {"summary": "elevation"},
    }


@web.route("/interactive-map/<string:state>/<string:name>")
def interactive_map(state, name):
    debug_mode = request.args.get("debug") == "true"

    db_path = current_app.config["DATABASE_PATH"]
    mountain = _load_mountain_or_404(state, name, db_path)

    trails, lifts = _sorted_trails_and_lifts(mountain)
    geojson = _build_geojson(mountain, trails, lifts, debug_mode)

    return render_template(
        "interactive_map.jinja",
        active_page="map",
        geojson=geojson,
        mountain=mountain,
        trails=trails,
        lifts=lifts,
    )


@web.route("/sitemap.xml")
def site_map():
    db_path = current_app.config["DATABASE_PATH"]
    mountains, _ = list_mountains(db_path=db_path)

    url_template = (
        "<url><loc>https://steepseeker.com/{path}</loc>"
        "<changefreq>monthly</changefreq><priority>{priority}</priority></url>"
    )
    static_pages = [
        ("", 1),
        ("about", 0.6),
        ("search", 0.7),
        ("explore-map", 0.8),
        ("rankings", 0.9),
        ("trail-rankings", 0.9),
        ("lift-rankings", 0.8),
    ]
    dynamic_pages = ["map", "interactive-map"]
    dynamic_priority = 0.3

    xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for path, priority in static_pages:
        xml += url_template.format(path=path, priority=priority)
    for page in dynamic_pages:
        for mountain in mountains:
            xml += url_template.format(
                path=f"{page}/{mountain.state.value}/{mountain.name}",
                priority=dynamic_priority,
            )
    xml += "</urlset>"

    return Response(xml, mimetype="text/xml")
