import time
from typing import List, Tuple, Optional
import requests
import shapely

from core.connectors.database import cursor, CACHE_DB_PATH


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
        Uses cache when available.
        """
        if not nodes:
            return []

        # Round before using as a cache key -- upstream geometry math
        # (reprojection round-trips, resampling) leaves float noise past the
        # 6th decimal place that would otherwise miss the cache even though
        # the point is the same one already cached.
        nodes = [(round(lon, 6), round(lat, 6)) for lon, lat in nodes]

        # Create point strings for all nodes
        node_points = {str(shapely.Point(lon, lat)): (lon, lat) for lon, lat in nodes}

        # Batch query cache
        cached_results = {}
        with cursor(CACHE_DB_PATH, dict_cursor=False) as cur:
            placeholders = ",".join("?" * len(node_points))
            query = f"SELECT point, elevation FROM CachedPoints WHERE point IN ({placeholders})"
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
                    "INSERT OR REPLACE INTO CachedPoints (point, elevation) VALUES (?, ?)",
                    cache_data,
                )

        # Combine cached and API results in original order
        results = []
        for lon, lat in nodes:
            point_str = str(shapely.Point(lon, lat))
            elevation = cached_results.get(point_str) or api_results.get(point_str)
            results.append([lon, lat, elevation])

        if len(results) != len(nodes):
            print("mismatch in point counts")
            raise ValueError("Mismatch in number of coordinates vs elevation results")

        return results

    def _query_api(
        self, nodes: List[Tuple[float, float]], spacing: int = 100
    ) -> List[Tuple[float, float, float]]:
        """
        Internal method to query the elevation API.
        """

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

        return results
