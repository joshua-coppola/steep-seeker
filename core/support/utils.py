from math import atan, ceil, degrees

import haversine as hs
import numpy as np
import pyproj
import shapely
import shapely.ops

COORDINATE_PRECISION = 6
METERS_TO_FEET = 3.28084


def meters_to_feet(value: float | None) -> float | None:
    """
    Converts a meters value (how length/vertical are stored internally,
    matching the elevation API and geometry math) to feet, for display to
    the end user. Passes None through unchanged.
    """
    if value is None:
        return None

    return value * METERS_TO_FEET


def round_feet(value: float | None) -> int | None:
    """
    Rounds a feet value to the nearest whole foot, for display to the end
    user. Passes None through unchanged.
    """
    if value is None:
        return None

    return round(value)


def round_degrees(value: float | None) -> float | None:
    """
    Rounds a degrees value (difficulty, beginner_friendliness, max_slope,
    average_slope, steepest_Xm) to the nearest 0.1 degree, for display to
    the end user. Passes None through unchanged.
    """
    if value is None:
        return None

    return round(value, 1)


def trail_color(difficulty: float) -> str:
    """
    Maps a difficulty/pitch value (degrees) to the site's standard trail
    color scale, used for both static map rendering and interactive-map
    popups.
    """
    # 0-18 degrees: green
    if difficulty < 18:
        return "green"
    # 18-27 degrees: blue
    if difficulty < 27:
        return "royalblue"
    # 27-36 degrees: black
    if difficulty < 36:
        return "black"
    # 36-47 degrees: red
    if difficulty < 47:
        return "red"
    # >47 degrees: yellow
    return "gold"


def round_geometry_precision(
    geometry: shapely.geometry.base.BaseGeometry,
    ndigits: int = COORDINATE_PRECISION,
) -> shapely.geometry.base.BaseGeometry:
    """
    Returns a copy of the given geometry with its x/y coordinates rounded to
    `ndigits` decimal places (6dp is ~11cm). Elevation (z), if present, is
    left untouched. Call this on any geometry right before it's persisted,
    so precision is guaranteed at the DB boundary regardless of how the
    geometry's coordinates were produced upstream.
    """

    def _round(coords: np.ndarray) -> np.ndarray:
        coords = coords.copy()
        coords[:, :2] = np.round(coords[:, :2], ndigits)
        return coords

    return shapely.transform(geometry, _round, include_z=geometry.has_z)


def get_bounding_box(
    geometries: list[shapely.geometry.base.BaseGeometry], padding: float = 0
) -> str:
    """
    Returns an Overpass-API-formatted "min_lon,min_lat,max_lon,max_lat"
    bounding box string covering the given geometries, expanded outward
    by `padding` as a fraction of each dimension (e.g. 0.5 adds 50% to
    each side) -- for re-fetching an OSM extract that still covers a
    mountain after new trails/lifts have been added just past its
    original edges.
    """
    bounds = [geometry.bounds for geometry in geometries]
    min_lon = min(b[0] for b in bounds)
    min_lat = min(b[1] for b in bounds)
    max_lon = max(b[2] for b in bounds)
    max_lat = max(b[3] for b in bounds)

    lon_adj = (max_lon - min_lon) * padding * 0.5
    lat_adj = (max_lat - min_lat) * padding * 0.5

    return (
        f"{min_lon - lon_adj},{min_lat - lat_adj},"
        f"{max_lon + lon_adj},{max_lat + lat_adj}"
    )


def space_line_points_evenly(
    line: shapely.LineString, spacing_feet: int = 20
) -> shapely.LineString:
    """
    Accepts a Shapely LineString, and evenly spaces out points
    every 20 feet along the length of the line
    """
    wgs84 = pyproj.CRS("EPSG:4326")
    albers = pyproj.CRS("EPSG:5070")  # Equal Area projection for contiguous US

    to_meters_proj = pyproj.Transformer.from_proj(wgs84, albers, always_xy=True)

    to_coordinates = pyproj.Transformer.from_proj(albers, wgs84, always_xy=True)

    line_proj = shapely.ops.transform(to_meters_proj.transform, line)

    # Convert feet to meters because EPSG:5070 is in meters
    spacing_meters = spacing_feet / 3.28084
    num_points = ceil(line_proj.length / spacing_meters)
    distances = [i * spacing_meters for i in range(num_points + 1)]

    points_proj = [line_proj.interpolate(d) for d in distances]
    points_geo = [
        shapely.ops.transform(to_coordinates.transform, pt) for pt in points_proj
    ]

    return shapely.LineString(points_geo)


def space_polygon_exterior_points_evenly(
    polygon: shapely.Polygon, spacing_feet: int = 20
) -> shapely.Polygon:
    """
    Accepts a Shapely Polygon, and evenly spaces out points
    every 20 feet along the perimeter of the Polygon
    """
    line = space_line_points_evenly(polygon.exterior, spacing_feet)

    return shapely.Polygon(line)


def polygon_interior_grid(
    polygon: shapely.Polygon, spacing_feet: int = 20
) -> shapely.MultiPoint:
    """
    Accepts a Shapely Polygon and returns a grid of points that
    fall inside the polygon boundry at a set interval defined in feet.
    """
    wgs84 = pyproj.CRS("EPSG:4326")
    albers = pyproj.CRS("EPSG:5070")  # Equal Area projection for contiguous US

    to_meters_proj = pyproj.Transformer.from_proj(wgs84, albers, always_xy=True)

    to_coordinates = pyproj.Transformer.from_proj(albers, wgs84, always_xy=True)

    polygon_proj = shapely.ops.transform(to_meters_proj.transform, polygon)

    minx, miny, maxx, maxy = polygon_proj.bounds

    # Create grid coordinates
    spacing_meters = spacing_feet / 3.28084
    x_coords = np.arange(minx, maxx, spacing_meters)
    y_coords = np.arange(miny, maxy, spacing_meters)
    X, Y = np.meshgrid(x_coords, y_coords)

    # Flatten into Nx2 array
    coords = np.column_stack((X.ravel(), Y.ravel()))

    # Build multipoint from all candidate points
    mp = shapely.MultiPoint(coords)

    # Intersection keeps only points inside polygon
    inside_proj = polygon_proj.intersection(mp)
    inside = shapely.ops.transform(to_coordinates.transform, inside_proj)

    # Normalize return type
    if inside.is_empty:
        return None
    elif inside.geom_type == "Point":
        return shapely.MultiPoint([inside])
    elif inside.geom_type == "MultiPoint":
        return inside
    elif inside.geom_type == "GeometryCollection":
        # filter only points
        pts = [g for g in inside.geoms if g.geom_type == "Point"]
        return shapely.MultiPoint(pts) if pts else None
    else:
        raise ValueError(f"Unexpected geometry type: {inside.geom_type}")


def get_length(geometry: dict[str, str]) -> float:
    """
    Accepts a geojson LineString blob (flat "coordinates" list of points)
    and calculates the haversine distance of the line. For an area trail,
    pass its route rather than its boundary polygon -- a ring's nested
    coordinate structure isn't a line to walk along.
    """
    previous_point = None
    cumulative_dist = 0

    for i, point in enumerate(geometry["coordinates"]):
        if i == 0:
            previous_point = point
            continue

        # Haversine expects (lat, lon)
        dist = hs.haversine(
            (previous_point[1], previous_point[0]),
            (point[1], point[0]),
            unit=hs.Unit.METERS,
        )
        cumulative_dist += dist
        previous_point = point

    return cumulative_dist


def get_vertical_drop(geometry: dict[str, str]) -> float | None:
    """
    Accepts a geojson blob and calculates vertical drop (max elevation - min elevation).
    Returns meters or `None` if no elevation data is available.
    """
    elevations = []

    coords = geometry.get("coordinates") or []

    def _extract(points):
        for p in points:
            # nested coordinate lists (e.g., polygons) can appear as lists of lists
            if isinstance(p, (list, tuple)) and p and isinstance(p[0], (list, tuple)):
                _extract(p)
            else:
                # expect [lon, lat, elevation] or [lon, lat]
                if isinstance(p, (list, tuple)) and len(p) >= 3:
                    elev = p[2]
                    if elev is not None:
                        elevations.append(float(elev))

    _extract(coords)

    if not elevations:
        return None

    return max(elevations) - min(elevations)


def get_slope_profile(geometry: dict[str, str]) -> list[float]:
    """
    Accepts a geojson LineString blob (flat "coordinates" list of points)
    and calculates the slope in degrees between each consecutive pair of
    points, based on elevation change and horizontal (haversine) distance.
    Returns one slope value per segment. For an area trail, pass its route
    rather than its boundary polygon -- a ring's nested coordinate
    structure isn't a line to walk along.
    """
    coordinates = geometry.get("coordinates") or []

    slopes = []
    previous_point = None

    for point in coordinates:
        if previous_point is None:
            previous_point = point
            continue

        if (
            len(previous_point) < 3
            or len(point) < 3
            or previous_point[2] is None
            or point[2] is None
        ):
            previous_point = point
            continue

        dist = hs.haversine(
            (previous_point[1], previous_point[0]),
            (point[1], point[0]),
            unit=hs.Unit.METERS,
        )
        elevation_change = point[2] - previous_point[2]

        if dist == 0:
            slopes.append(0.0)
        else:
            slopes.append(abs(degrees(atan(elevation_change / dist))))

        previous_point = point

    return slopes


def build_elevation_profile(
    coords: list[tuple[float, float, float]],
) -> list[list[float]]:
    """
    Converts an ordered list of (lon, lat, elevation_meters) points, for
    example from Trail.geometry.coords, Trail.geometry.exterior.coords for an
    area trail's boundary ring, or Trail.route.coords into the
    [lon, lat, elevation_feet, slope_degrees] point array the interactive
    map's elevation profile (leaflet.heightgraph) expects. slope_degrees is
    the raw point-to-point pitch (no difficulty modifiers applied); the
    first point's slope is 0.
    """
    profile = []
    previous_point = None

    for lon, lat, elevation_m in coords:
        slope = 0.0
        if previous_point is not None:
            prev_lon, prev_lat, prev_elevation_m = previous_point
            dist = hs.haversine((prev_lat, prev_lon), (lat, lon), unit=hs.Unit.METERS)
            elevation_change = prev_elevation_m - elevation_m
            if dist != 0 and elevation_change != 0:
                slope = abs(degrees(atan(elevation_change / dist)))

        profile.append(
            [lon, lat, round_feet(meters_to_feet(elevation_m)), round_degrees(slope)]
        )
        previous_point = (lon, lat, elevation_m)

    return profile


def get_max_slope(geometry: dict[str, str]) -> float | None:
    """
    Accepts a geojson blob and returns the steepest segment-to-segment
    slope in degrees, or `None` if it can't be calculated.
    """
    slopes = get_slope_profile(geometry)

    return max(slopes) if slopes else None


def get_average_slope(geometry: dict[str, str]) -> float | None:
    """
    Accepts a geojson blob and returns the average segment-to-segment
    slope in degrees, or `None` if it can't be calculated.
    """
    slopes = get_slope_profile(geometry)

    return sum(slopes) / len(slopes) if slopes else None


def get_steepest_pitch(geometry: dict[str, str], window_meters: float) -> float | None:
    """
    Accepts a geojson LineString blob (flat "coordinates" list of points)
    and returns the steepest slope in degrees found over any contiguous
    window of at least `window_meters` along the line. For an area trail,
    pass its route rather than its boundary polygon -- a ring's nested
    coordinate structure isn't a line to walk along.

    If the trail is shorter than the window, falls back to the overall
    trail slope for windows of 30m or less (the trail is short enough that
    its whole length is a reasonable stand-in); for longer windows there's
    no meaningful window-sized measurement, so `None` is returned.
    """
    coordinates = geometry.get("coordinates") or []

    if len(coordinates) < 2:
        return None

    max_pitch = None

    for start, start_point in enumerate(coordinates):
        if len(start_point) < 3 or start_point[2] is None:
            continue

        cumulative_dist = 0
        previous_point = start_point

        for point in coordinates[start + 1 :]:
            cumulative_dist += hs.haversine(
                (previous_point[1], previous_point[0]),
                (point[1], point[0]),
                unit=hs.Unit.METERS,
            )
            previous_point = point

            if cumulative_dist >= window_meters:
                if len(point) >= 3 and point[2] is not None:
                    elevation_change = start_point[2] - point[2]
                    pitch = (
                        abs(degrees(atan(elevation_change / cumulative_dist)))
                        if elevation_change != 0
                        else 0.0
                    )
                    if max_pitch is None or pitch > max_pitch:
                        max_pitch = pitch
                break

    if max_pitch is not None:
        return round(max_pitch, 1)

    if window_meters > 30:
        return None

    first_point, last_point = coordinates[0], coordinates[-1]
    if (
        len(first_point) < 3
        or len(last_point) < 3
        or first_point[2] is None
        or last_point[2] is None
    ):
        return None

    total_dist = get_length(geometry)
    if total_dist == 0:
        return 0.0

    elevation_change = last_point[2] - first_point[2]

    return round(
        abs(degrees(atan(elevation_change / total_dist)))
        if elevation_change != 0
        else 0.0,
        1,
    )


def get_trail_difficulty(
    steepest_30m: float | None,
    gladed: bool,
    ungroomed: bool,
    weather_modifier: float,
) -> float | None:
    """
    Accepts a trail's steepest 30m pitch, its gladed/ungroomed flags, and
    the mountain's weather modifier (see connectors.weather_api), and
    returns the trail's overall difficulty rating. Returns `None` if
    steepest_30m couldn't be calculated.

    A trail that is both gladed and ungroomed only gets the gladed modifier;
    the two aren't stacked.
    """
    if steepest_30m is None:
        return None

    difficulty = steepest_30m + weather_modifier

    if gladed:
        difficulty += 5.5
    elif ungroomed:
        difficulty += 2.5

    return round(difficulty, 1)


def get_mountain_rating(
    trail_difficulties: list[float],
) -> tuple[float | None, float | None]:
    """
    Accepts the difficulty ratings of a mountain's trails and returns
    (difficulty, beginner_friendliness) for the mountain overall, or
    (None, None) if no trail difficulties were given.

    Each value blends a top/bottom-30 average (20% weight) with a
    top/bottom-5 average (80% weight) - difficulty from the hardest trails,
    beginner_friendliness from the easiest - so a mountain with a handful of
    standout hard or easy trails is rated accordingly without being fully
    dominated by outliers.
    """
    if not trail_difficulties:
        return None, None

    sorted_difficulties = sorted(trail_difficulties, reverse=True)

    wide_count = min(30, len(sorted_difficulties))
    narrow_count = min(5, wide_count)

    def weighted_average(values: list[float]) -> float:
        wide = values[:wide_count]
        narrow = values[:narrow_count]
        return (sum(wide) / wide_count) * 0.2 + (sum(narrow) / narrow_count) * 0.8

    difficulty = weighted_average(sorted_difficulties)
    beginner_friendliness = weighted_average(list(reversed(sorted_difficulties)))

    return round(difficulty, 1), round(beginner_friendliness, 1)
