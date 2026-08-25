import requests


class OSM:
    """Fetches raw OSM XML extracts from the Overpass API."""

    BASE_URL = "https://overpass-api.de/api/map"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def get(self, bounding_box: str) -> bytes | None:
        """
        Fetch a raw OSM XML extract for the given bounding box
        ("min_lon,min_lat,max_lon,max_lat"). Retries up to 3 times on a
        504 (Overpass's usual response when a request times out
        server-side), and gives up immediately on any other non-200
        status. Returns None on failure.
        """
        params = {"bbox": bounding_box}

        for _ in range(3):
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            if response.status_code == 200:
                return response.content
            if response.status_code != 504:
                return None

        return None
