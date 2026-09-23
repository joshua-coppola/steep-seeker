import random
from dataclasses import asdict, dataclass
from math import atan2, degrees
from urllib.parse import urlencode

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import escape

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.lift_query import list_lifts
from core.support.mountain import Mountain
from core.support.mountain_query import list_mountains
from core.support.trail_query import list_trails
from core.support.utils import (
    BEGINNER_FRIENDLINESS_FLIP,
    DIFFICULTY_CONSTANTS,
    PITCH_WINDOW_LABELS,
    beginner_color,
    build_elevation_profile,
    difficulty_pitch_field,
    display_beginner_friendliness,
    round_degrees,
    trail_color,
    weather_modifier_from_trail,
)

web = Blueprint("web", __name__)


@web.app_context_processor
def inject_rating_colors():
    # so templates can color a difficulty / beginner-friendliness number
    # the same way the Python serving code does, and build their own
    # threshold comparisons (search/rankings) from the same live constants
    # instead of hardcoding copies of them
    return {
        "trail_color": trail_color,
        "beginner_color": beginner_color,
        # a dict (not the dataclass instance) so it works with both Jinja's
        # dot-access convenience and the |tojson filter that hands it to
        # search.js/interactive-map.js via page_base.jinja
        "difficulty_thresholds": asdict(DIFFICULTY_CONSTANTS),
        "beginner_friendliness_max": BEGINNER_FRIENDLINESS_FLIP,
        "display_beginner_friendliness": display_beginner_friendliness,
    }


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


def _int_arg(
    name: str, default: int, minimum: int | None = None, maximum: int | None = None
) -> int:
    """
    Reads an int query param, falling back to `default` when it's missing,
    blank, or not a number (rather than 500ing), then clamping to
    [minimum, maximum] when those are given.
    """
    try:
        value = int(request.args.get(name) or default)
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def _float_arg(name: str, default: float) -> float:
    """
    Reads a float query param, falling back to `default` when it's missing,
    blank, or not a number. "Infinity" parses natively (search.js sends it
    for a maxed-out slider handle).
    """
    try:
        return float(request.args.get(name) or default)
    except (TypeError, ValueError):
        return default


def _pagination_url(base_path: str, target_page: int) -> str:
    """
    Current request's query string with `page` swapped to target_page,
    for a list page's prev/next links.
    """
    args = request.args.to_dict()
    args["page"] = str(target_page)
    return f"{base_path}?{urlencode(args)}"


@web.route("/search", methods=["GET", "POST"])
def search():
    q = (request.args.get("q") or "").strip()
    page = _int_arg("page", 1, minimum=1)
    limit = _int_arg("limit", 20, minimum=1)
    diffmin = _float_arg("diffmin", 0)
    diffmax = _float_arg("diffmax", 100)
    trailsmin = _float_arg("trailsmin", 0)
    trailsmax = _float_arg("trailsmax", 1000)
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

    pages = {}
    if total_mountain_count > limit and (limit * page) < total_mountain_count:
        pages["next"] = _pagination_url("/search", page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url("/search", page - 1)

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
    page = _int_arg("page", 1, minimum=1)
    limit = _int_arg("limit", 50, minimum=1, maximum=200)
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

    pages = {"offset": offset}
    if total_trail_count > limit and (limit * page) < total_trail_count:
        pages["next"] = _pagination_url("/trail-rankings", page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url("/trail-rankings", page - 1)
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
        pitch_fields=PITCH_WINDOW_LABELS,
    )


@web.route("/lift-rankings")
def lift_rankings():
    region_param = request.args.get("region") or "usa"
    state_param = request.args.get("state")
    if state_param == "None":
        state_param = None
    page = _int_arg("page", 1, minimum=1)
    limit = _int_arg("limit", 50, minimum=1, maximum=200)
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

    pages = {"offset": offset}
    if total_lift_count > limit and (limit * page) < total_lift_count:
        pages["next"] = _pagination_url("/lift-rankings", page + 1)
    if offset != 0:
        pages["prev"] = _pagination_url("/lift-rankings", page - 1)
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
    if len(lon_points) < 2:
        return 0

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
    is its boundary Polygon feature plus -- when a route has been computed
    for it -- a second, faint/non-interactive LineString feature (styled in
    interactive-map.js) carrying that route's elevation profile. The polygon's
    own properties carry the route's profile too (as routeCoordinates), so
    interactive-map.js can show a real heightgraph when the polygon
    itself is clicked.
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

    properties = {
        # name is the trail's identity (used for the elevation-profile
        # title regardless of which feature was clicked); label is
        # specifically the text drawn along the map -- the two diverge for
        # an area trail, whose label moves onto its route line below
        "name": trail.name,
        "label": trail.name,
        "orientation": orientation,
        "color": trail_color(trail.difficulty),
        "gladed": str(trail.gladed),
        "difficulty_modifier": (trail.difficulty or 0)
        - (getattr(trail, difficulty_pitch_field()) or 0),
        # unconditional (not just under debug_mode) since the management
        # edit map's delete-mode click-flagging and its popup's tag-edit/
        # delete forms both need it -- see interactive-map.js
        "item_id": trail.trail_id,
    }

    # Popup data is sent structured rather than as pre-rendered HTML --
    # interactive-map.js builds the actual popup lazily, only for whichever
    # trail gets clicked, instead of every one of a resort's trails (600+
    # for a large one) carrying a full baked-in HTML popup that bloats the
    # GeoJSON payload whether it's ever opened or not. The management edit
    # map's popup additionally gets a gladed/ungroomed/hazardous tag-edit
    # form and a delete form, appended client-side when editable.
    properties["popupData"] = {
        "kind": "trail",
        "name": trail.name,
        "difficulty": trail.difficulty,
        "color": trail_color(trail.difficulty),
        "gladed": trail.gladed,
        "ungroomed": trail.ungroomed,
        "hazardous": trail.hazardous,
        "length_feet": trail.length_feet(),
        "vertical_feet": trail.vertical_feet(),
        "pitches": [
            {"label": label, "value": value, "color": trail_color(value)}
            for field, label in PITCH_WINDOW_LABELS
            if (value := getattr(trail, field))
        ],
        "debug_id": trail.trail_id if debug_mode else None,
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


LIFT_TYPE_LABELS = {
    "cable_car": "Tram",
    "gondola": "Gondola",
    "mixed_lift": "Mixed Lift",
    "chair_lift": "Chairlift",
    "drag_lift": "Drag Lift",
    "t-bar": "T-Bar",
    "j-bar": "J-Bar",
    "platter": "Platter Lift",
    "rope_tow": "Rope Tow",
    "magic_carpet": "Magic Carpet",
    "hike": "Hike-to Access",
}


def _lift_type_label(lift_type: str) -> str:
    """
    Human-readable label for a Lift's lift_type -- OSM's aerialway tag
    values, plus "hike" for hike-to access routes stored as lifts (see
    core.osm.trail_parser.identify_hikes). Falls back to a titlecased
    version of the raw value for any aerialway type not in
    LIFT_TYPE_LABELS, since OSM tagging isn't a closed enum.
    """
    return LIFT_TYPE_LABELS.get(
        lift_type, lift_type.replace("_", " ").replace("-", " ").title()
    )


def _lift_feature(
    lift, direction: str, weather_modifier: float, debug_mode: bool
) -> dict:
    coords = list(lift.geometry.coords)
    profile = build_elevation_profile(coords)
    lon_points = [c[0] for c in coords]
    lat_points = [c[1] for c in coords]
    orientation = _orientation(lon_points, lat_points, False, direction)

    properties = {
        "name": lift.name,
        "label": lift.name,
        "orientation": orientation,
        "color": "grey",
        "lift_type": lift.lift_type,
        "difficulty_modifier": weather_modifier,
        # unconditional -- see the matching comment in _trail_features
        "item_id": lift.lift_id,
    }

    # See the matching comment in _trail_features above: structured data,
    # popup (including the management edit map's delete form) built
    # lazily client-side.
    properties["popupData"] = {
        "kind": "lift",
        "name": lift.name,
        "occupancy": lift.occupancy,
        "lift_type_label": _lift_type_label(lift.lift_type),
        "length_feet": lift.length_feet(),
        "vertical_feet": lift.vertical_feet(),
        "average_slope": round_degrees(lift.average_slope),
        "bubble": lift.bubble,
        "heating": lift.heating,
        "debug_id": lift.lift_id if debug_mode else None,
    }

    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "LineString", "coordinates": profile},
    }


@web.route("/explore-map")
def explore_map():
    db_path = current_app.config["DATABASE_PATH"]
    mountains, _ = list_mountains(db_path=db_path)

    features = []
    for mountain in mountains:
        difficulty_color = trail_color(mountain.difficulty)
        beginner_col = beginner_color(mountain.beginner_friendliness)

        popup_content = (
            f'<h3><a href="/interactive-map/{mountain.state.value}/{escape(mountain.name)}">'
            f"{escape(mountain.name)}</a></h3>"
        )
        for season_pass in mountain.season_passes:
            popup_content += (
                f'<img src="icons/{season_pass.value}.png" class="pass-icon"/>'
            )
        popup_content += (
            f"<p>Vertical: {mountain.vertical} ft</p>"
            f'<p>Difficulty: {mountain.difficulty}<span class="icon difficulty-{difficulty_color}"></span></p>'
            f'<p>Beginner Friendliness: {mountain.beginner_friendliness}<span class="icon difficulty-{beginner_col}"></span></p>'
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
    mountain.beginner_friendliness = display_beginner_friendliness(
        mountain.beginner_friendliness
    )

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
        weather_modifier=round_degrees(_weather_modifier(trails)),
    )


def _weather_modifier(trails: list) -> float:
    """
    Recovers the mountain's weather modifier alone (stripping the
    gladed/ungroomed bonus baked into trails[0]'s difficulty), since
    lifts don't carry their own difficulty_modifier
    """
    if not trails:
        return 0

    return weather_modifier_from_trail(trails[0])


def _build_geojson(
    mountain: Mountain, trails: list, lifts: list, debug_mode: bool
) -> dict:
    weather_modifier = _weather_modifier(trails)

    # Area trails first so ordinary trails always render on top of them.
    ordered_trails = [t for t in trails if t.area] + [t for t in trails if not t.area]

    features = []
    for trail in ordered_trails:
        features.extend(_trail_features(trail, mountain.direction, debug_mode))
    for lift in lifts:
        features.append(
            _lift_feature(lift, mountain.direction, weather_modifier, debug_mode)
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

    # trails/lifts are still needed here for the sidebar list, but the
    # GeoJSON itself (which can run into the megabytes for a large resort,
    # once every trail/lift's popup HTML is baked in) is fetched by the
    # browser separately (see interactive_map_geojson below) instead of
    # being inlined into this page's HTML, so the page shell can render
    # before that payload downloads.
    trails, lifts = _sorted_trails_and_lifts(mountain)

    return render_template(
        "interactive_map.jinja",
        active_page="map",
        mountain=mountain,
        trails=trails,
        lifts=lifts,
        debug_mode=debug_mode,
        weather_modifier=round_degrees(_weather_modifier(trails)),
    )


@web.route("/interactive-map/<string:state>/<string:name>/geojson")
def interactive_map_geojson(state, name):
    debug_mode = request.args.get("debug") == "true"

    db_path = current_app.config["DATABASE_PATH"]
    mountain = _load_mountain_or_404(state, name, db_path)
    trails, lifts = _sorted_trails_and_lifts(mountain)

    return jsonify(_build_geojson(mountain, trails, lifts, debug_mode))


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
