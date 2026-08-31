import time
from math import ceil

import requests
import shapely
from rich.progress import track

from core.connectors.database import CACHE_DB_PATH, cursor
from core.datamodels.database import CacheTable


class Elevation:
    last_called = 0.0

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def get(
        self,
        nodes: list[tuple[float, float]],
        spacing: int = 100,
    ) -> list[tuple[float, float, float]] | None:
        """
        Takes in a list of [lon, lat] nodes and queries the elevation API to get
        an elevation for each node. Returns a list of [lon, lat, elevation].
        Uses cache when available.
        """
        if not nodes:
            return []

        # Round before using as a cache key
        nodes = [(round(lon, 6), round(lat, 6)) for lon, lat in nodes]

        # Create point strings for all nodes
        node_points = {str(shapely.Point(lon, lat)): (lon, lat) for lon, lat in nodes}

        # Batch query cache
        cached_results = {}
        with cursor(CACHE_DB_PATH, dict_cursor=False) as cur:
            placeholders = ",".join("?" * len(node_points))
            query = f"SELECT {CacheTable.point}, {CacheTable.elevation} FROM CachedPoints WHERE {CacheTable.point} IN ({placeholders})"
            results = cur.execute(query, tuple(node_points.keys())).fetchall()

            for point_str, elevation in results:
                cached_results[point_str] = elevation

        # Find uncached nodes
        uncached_nodes = [
            node_points[point_str]
            for point_str in node_points
            if point_str not in cached_results
        ]

        # Query API for uncached points
        api_results = {}
        if uncached_nodes:
            api_data = self._query_api(uncached_nodes, spacing)

            # Batch insert new results into cache
            with cursor(CACHE_DB_PATH, dict_cursor=False) as cur:
                cache_data = []
                for lon, lat, elevation in api_data:
                    point_str = str(shapely.Point(lon, lat))
                    api_results[point_str] = elevation
                    cache_data.append((point_str, elevation))

                cur.executemany(
                    f"INSERT OR REPLACE INTO CachedPoints ({CacheTable.point}, {CacheTable.elevation}) VALUES (?, ?)",
                    cache_data,
                )

        # Combine cached and API results in original order. Check key
        # presence rather than truthiness so a real elevation of 0.0 (sea
        # level) isn't discarded and refetched as None.
        results = []
        for lon, lat in nodes:
            point_str = str(shapely.Point(lon, lat))
            if point_str in cached_results:
                elevation = cached_results[point_str]
            else:
                elevation = api_results.get(point_str)
            results.append([lon, lat, elevation])

        if len(results) != len(nodes):
            print("mismatch in point counts")
            raise ValueError("Mismatch in number of coordinates vs elevation results")

        return results

    def _query_api(
        self, nodes: list[tuple[float, float]], spacing: int = 100
    ) -> list[tuple[float, float, float]]:
        """
        Internal method to query the elevation API.
        """

        def divide_chunks(full_list, n):
            for i in range(0, len(full_list), n):
                yield full_list[i : i + n]

        url = "https://api.opentopodata.org/v1/ned10m?locations={}"
        results: list[tuple[float, float, float]] = []

        for chunk in track(
            divide_chunks(nodes, spacing),
            total=ceil(len(nodes) / spacing),
            description=f"Fetching elevation for {len(nodes)} points",
        ):
            # Build location string like "lat,lon|lat,lon|..."
            coords_str = "|".join(f"{lat},{lon}" for lon, lat in chunk)

            # Respect 1 req/s rate limit
            elapsed = time.monotonic() - Elevation.last_called
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

            response = requests.get(url.format(coords_str), timeout=self.timeout)
            Elevation.last_called = time.monotonic()

            if response.status_code != 200:
                raise RuntimeError(
                    f"Elevation API call failed with {response.status_code}: {response.text}"
                )

            data = response.json()["results"]

            # Pair back to (lat, lon) from chunk
            for (lon, lat), entry in zip(chunk, data):
                results.append([lon, lat, entry["elevation"]])

        return results
