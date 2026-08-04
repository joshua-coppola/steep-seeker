import shapely
import shapely.ops
import pyproj
from math import ceil, atan, degrees
import numpy as np
import haversine as hs
from typing import Dict, List, Optional

from core.support.trail import Trail
from core.support.lift import Lift


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
    
def get_length(geometry: Dict[str, str]) -> float:
    """
    Accepts a geojson blob and calculates the haversine distance of the line
    """
    # TODO: Handle areas correctly

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


def get_vertical_drop(geometry: Dict[str, str]) -> Optional[float]:
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


def get_slope_profile(geometry: Dict[str, str]) -> List[float]:
    """
    Accepts a geojson blob and calculates the slope in degrees between
    each consecutive pair of points, based on elevation change and
    horizontal (haversine) distance. Returns one slope value per segment.
    """
    # TODO: Handle areas correctly
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


def get_max_slope(geometry: Dict[str, str]) -> Optional[float]:
    """
    Accepts a geojson blob and returns the steepest segment-to-segment
    slope in degrees, or `None` if it can't be calculated.
    """
    slopes = get_slope_profile(geometry)

    return max(slopes) if slopes else None


def get_average_slope(geometry: Dict[str, str]) -> Optional[float]:
    """
    Accepts a geojson blob and returns the average segment-to-segment
    slope in degrees, or `None` if it can't be calculated.
    """
    slopes = get_slope_profile(geometry)

    return sum(slopes) / len(slopes) if slopes else None


def get_steepest_pitch(
    geometry: Dict[str, str], window_meters: float
) -> Optional[float]:
    """
    Accepts a geojson blob and returns the steepest slope in degrees found
    over any contiguous window of at least `window_meters` along the line.

    If the trail is shorter than the window, falls back to the overall
    trail slope for windows of 30m or less (the trail is short enough that
    its whole length is a reasonable stand-in); for longer windows there's
    no meaningful window-sized measurement, so `None` is returned.
    """
    # TODO: Handle areas correctly
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
