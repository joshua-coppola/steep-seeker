import time
from typing import List, Tuple, Optional
import requests


def get_elevation(
    nodes: List[Tuple[float, float]], spacing: int = 100
) -> Optional[List[Tuple[float, float, float]]]:
    """
    Takes in a list of (lat, lon) nodes and queries the elevation API to get
    an elevation for each node. Returns a list of (lat, lon, elevation).
    """
    if not nodes:
        return []

    def divide_chunks(full_list, n):
        for i in range(0, len(full_list), n):
            yield full_list[i : i + n]

    url = "https://api.opentopodata.org/v1/ned10m?locations={}"

    results: List[Tuple[float, float, float]] = []
    last_called = 0.0

    for chunk in divide_chunks(nodes, spacing):
        # Build location string like "lat,lon|lat,lon|..."
        coords_str = "|".join(f"{lat},{lon}" for lat, lon in chunk)

        # Respect 1 req/s rate limit
        elapsed = time.monotonic() - last_called
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        response = requests.get(url.format(coords_str))
        last_called = time.monotonic()

        if response.status_code != 200:
            raise RuntimeError(
                f"Elevation API call failed with {response.status_code}: {response.text}"
            )

        data = response.json()["results"]
        print(data)

        # Pair back to (lat, lon) from chunk
        for (lat, lon), entry in zip(chunk, data):
            results.append((lat, lon, entry["elevation"]))

    if len(results) != len(nodes):
        raise ValueError("Mismatch in number of coordinates vs elevation results")

    return results
