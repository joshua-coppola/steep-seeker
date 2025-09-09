import shapely
import shapely.ops
import pyproj
from math import ceil
import numpy as np


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
