import shapely
import shapely.ops
import pyproj
from math import ceil


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
