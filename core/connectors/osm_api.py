from typing import ClassVar

import requests


class OSM:
    """Fetches raw OSM XML extracts from the Overpass API."""

    BASE_URL = "https://overpass-api.de/api/interpreter"
    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": "SteepSeeker/1.0 (+https://steepseeker.com)"
    }

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def get(self, bounding_box: str) -> bytes | None:
        """
        Fetch a raw OSM XML extract for the given bounding box
        ("min_lon,min_lat,max_lon,max_lat"), filtered server-side to just
        piste (trail) and aerialway (lift) ways/relations plus their
        referenced nodes -- osm.trail_parser never reads any other tag,
        and everything else OSM has mapped in a resort's bounding box
        (roads, buildings, land use, etc.) is the large majority of a
        full bounding-box dump by both way count and download size.
        Verified against real resorts (including one with relation-merged
        trails): identical parsed trails/lifts, 16-27x smaller download.

        Retries up to 3 times on a 504 (Overpass's usual response when a
        request times out server-side), and gives up immediately on any
        other non-200 status. Returns None on failure.
        """
        min_lon, min_lat, max_lon, max_lat = bounding_box.split(",")
        # Overpass QL's (bbox) filter is (south,west,north,east), unlike
        # the "min_lon,min_lat,max_lon,max_lat" convention used elsewhere
        # in this codebase (get_bounding_box, the old /api/map bbox param)
        overpass_bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        query = (
            f"[out:xml][timeout:{self.timeout}];"
            f'(way["piste:type"]({overpass_bbox});'
            f'way["aerialway"]({overpass_bbox});'
            f'relation["piste:type"]({overpass_bbox}););'
            "(._;>;);"
            "out body;"
        )

        for _ in range(3):
            response = requests.post(
                self.BASE_URL,
                data={"data": query},
                timeout=self.timeout,
                headers=self.HEADERS,
            )
            if response.status_code == 200:
                return response.content
            if response.status_code != 504:
                return None

        return None
