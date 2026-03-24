import time
from typing import List, Tuple, Optional
import requests


class Elevation:
    last_called = 0.0

    def __init__(self):
        pass

    def get(
        self,
        nodes: List[Tuple[float, float]],
        spacing: int = 100,
    ) -> Optional[List[Tuple[float, float, float]]]:
        """
        Takes in a list of [lon, lat] nodes and queries the elevation API to get
        an elevation for each node. Returns a list of [lon, lat, elevation].
        """
        if not nodes:
            return []

        def divide_chunks(full_list, n):
            for i in range(0, len(full_list), n):
                yield full_list[i : i + n]

        url = "https://api.opentopodata.org/v1/ned10m?locations={}"

        results: List[Tuple[float, float, float]] = []

        for chunk in divide_chunks(nodes, spacing):
            # Build location string like "lat,lon|lat,lon|..."
            coords_str = "|".join(f"{lat},{lon}" for lon, lat in chunk)

            # Respect 1 req/s rate limit
            elapsed = time.monotonic() - Elevation.last_called
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

            response = requests.get(url.format(coords_str))
            Elevation.last_called = time.monotonic()

            if response.status_code != 200:
                raise RuntimeError(
                    f"Elevation API call failed with {response.status_code}: {response.text}"
                )

            data = response.json()["results"]

            # Pair back to (lat, lon) from chunk
            for (lon, lat), entry in zip(chunk, data):
                results.append([lon, lat, entry["elevation"]])

        if len(results) != len(nodes):
            print("mismatch in point counts")
            raise ValueError("Mismatch in number of coordinates vs elevation results")

        return results
