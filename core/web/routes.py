import random
from dataclasses import dataclass
from math import atan2, degrees
from urllib.parse import urlencode

from flask import (
    Blueprint,
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
    return render_template("index.jinja", nav_links=nav_links, active_page="index")


@web.route("/about")
def about():
    return render_template("about.jinja", nav_links=nav_links, active_page="about")


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
    filter" -- an unparseable state should return zero results, the way
    filtering by a real but non-matching state would, not silently show
    everything.
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
        nav_links=nav_links,
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
        nav_links=nav_links,
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
        nav_links=nav_links,
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


def _trail_features(trail, direction: str, debug_mode: bool) -> list[dict]:
    """
    Builds the GeoJSON feature(s) for one trail. A line trail is a single
    LineString feature. An area trail (glade/bowl, sampled as a polygon)
    is its boundary Polygon feature plus -- when a route (the least-steep
    path down the area) has been computed for it -- a second, faint/
    non-interactive LineString feature (styled in interactive-map.js)
    carrying that route's elevation profile. The polygon's own properties
    carry the route's profile too (as routeCoordinates), so
    interactive-map.js can show a real heightgraph when the polygon
    itself is clicked, rather than the "N/A" a bare Polygon feature would
    otherwise get.
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
    lift, direction: str, weather_modifier: float, debug_mode: bool
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


def _load_mountain_or_404(state: str, name: str, db_path: str) -> Mountain:
    state_enum = _parse_state(state)
    if not isinstance(state_enum, State):
        abort(404)

    mountain = Mountain.from_name(name, state_enum, db_path)
    if mountain is None:
        abort(404)

    return mountain


def _named_trails_and_lifts(mountain: Mountain) -> tuple[list, list]:
    """
    Returns (trails, lifts): named trails sorted by difficulty descending
    (unnamed connectors are excluded), and named lifts. Shared by /map and
    /interactive-map's sidebar + (for interactive-map) GeoJSON building.
    """
    trails = sorted(
        (t for t in mountain.trails.values() if t.name),
        key=lambda t: t.difficulty if t.difficulty is not None else -1,
        reverse=True,
    )
    lifts = [lift for lift in mountain.lifts.values() if lift.name]

    return trails, lifts


@web.route("/map/<string:state>/<string:name>")
def static_map(state, name):
    db_path = current_app.config["DATABASE_PATH"]
    mountain = _load_mountain_or_404(state, name, db_path)

    trails, lifts = _named_trails_and_lifts(mountain)

    return render_template(
        "map.jinja",
        nav_links=nav_links,
        active_page="map",
        mountain=mountain,
        trails=trails,
        lifts=lifts,
    )


@web.route("/interactive-map/<string:state>/<string:name>")
def interactive_map(state, name):
    debug_mode = request.args.get("debug") == "true"

    db_path = current_app.config["DATABASE_PATH"]
    mountain = _load_mountain_or_404(state, name, db_path)

    trails, lifts = _named_trails_and_lifts(mountain)

    # Recovers the mountain's weather modifier alone (stripping the
    # gladed/ungroomed bonus baked into trails[0]'s difficulty)
    weather_modifier = 0
    if trails:
        first = trails[0]
        if first.difficulty is not None and first.steepest_30m is not None:
            weather_modifier = (
                first.difficulty
                - first.steepest_30m
                - (5.5 if first.gladed else 0)
                - (2.5 if first.ungroomed else 0)
            )

    features = []
    for trail in trails:
        features.extend(_trail_features(trail, mountain.direction, debug_mode))
    for lift in lifts:
        features.append(
            _lift_feature(lift, mountain.direction, weather_modifier, debug_mode)
        )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {"summary": "elevation"},
    }

    return render_template(
        "interactive_map.jinja",
        nav_links=nav_links,
        active_page="map",
        geojson=geojson,
        mountain=mountain,
        trails=trails,
        lifts=lifts,
    )
