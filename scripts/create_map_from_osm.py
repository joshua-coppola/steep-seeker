"""
Reads a mountain from an OSM file and creates its map SVG.

Usage: python3 scripts/create_map_from_osm.py path/to/mountain.osm
"""

import sys

from core.connectors.weather_api import Weather
from core.support.maps import create_map, create_thumbnail
from core.support.mountain import Mountain

if __name__ == "__main__":
    osm_file = sys.argv[1]

    mountain = Mountain.from_osm(osm_file, season_passes=[], url="")
    create_map(mountain)
    create_thumbnail(mountain)

    weather = {
        "icy_days": mountain.average_icy_days,
        "rain": mountain.average_rain,
        "snow": mountain.average_snow,
    }
    print(f"Average icy days: {weather['icy_days']}")
    print(f"Average rain: {weather['rain']}")
    print(f"Average snow: {weather['snow']}")
    print(f"Weather modifier: {Weather.get_modifier(weather)}")
