import time
from datetime import datetime, timezone
from typing import ClassVar

import requests
from shapely import Point

from core.connectors.database import CACHE_DB_PATH, cursor
from core.datamodels.database import CachedWeatherTable


class Weather:
    """Fetches and processes historical weather data for ski season analysis."""

    # Class constants
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    WINTER_MONTHS: ClassVar[list[int]] = [11, 12, 1, 2, 3, 4]  # Nov - April
    FREEZE_THRESHOLD_HIGH = 34  # °F
    FREEZE_THRESHOLD_LOW = 32  # °F

    # Coordinate precision (decimal places) for the weather cache key. Matches
    # the elevation cache (CachedPoints) so both caches round the same way;
    # the key is str(shapely.Point(lon, lat)), same as CachedPoints.
    CACHE_COORD_PRECISION = 6

    # Statistics below are from the historical resort population (updated 2023-12-28):
    #   Metric       | Mean              | Standard Deviation
    #   icy_days     | 40.13571428571428 | 18.81610659373872
    #   snow         | 79.67810714285716 | 61.38204737243106
    #   rain         | 4.711321428571425 | 4.6343473924412
    # The min/max bounds below are +/- 2 standard deviations from the mean,
    # i.e. the range of non-outlier values.
    MIN_ICY_DAYS = 2.5
    MAX_ICY_DAYS = 77.78
    MAX_SNOW = 202.44
    MAX_RAIN = 13.97

    def __init__(self, num_seasons: int = 5, timezone: str = "America/New_York"):
        """
        Initialize Weather API client.

        Args:
            num_seasons: Number of past seasons to analyze (default: 5)
            timezone: Timezone for the location (default: America/New_York)
        """
        self.num_seasons = num_seasons
        self.timezone = timezone

    def _latest_season(self) -> int:
        """
        Calendar year in which the most recent *completed* winter started.

        A winter is "season N" if it runs Nov of year N through April of
        year N+1. Only winters that have fully finished (we are past April)
        are eligible, so cached seasons never hold in-progress data.
        """
        now = datetime.now(timezone.utc)
        last_winter_month = self.WINTER_MONTHS[-1]  # April

        # If we're past April, the winter that ended this April is complete;
        # otherwise the latest complete winter ended last April.
        end_year = now.year if now.month > last_winter_month else now.year - 1
        return end_year - 1

    def _needed_seasons(self) -> list[int]:
        """The `num_seasons` most recent completed winters, oldest first."""
        latest = self._latest_season()
        return list(range(latest - self.num_seasons + 1, latest + 1))

    def get(self, coordinate: Point) -> dict[str, float]:
        """
        Fetch and process historical weather data for a location.

        Historical winter weather is finalized and never changes, so each
        (rounded coordinate, season) is fetched from the API at most once and
        cached permanently. A refresh only pays for winters not already
        cached -- typically zero or one.

        Args:
            coordinate: Shapely point containing a lat/lon

        Returns:
            Dictionary with averaged winter weather metrics:
                - icy_days: Average freeze-thaw days per season
                - rain: Average rain total per season (inches)
                - snow: Average snowfall total per season (inches)
        """
        lat = round(coordinate.y, self.CACHE_COORD_PRECISION)
        lon = round(coordinate.x, self.CACHE_COORD_PRECISION)
        point = str(Point(lon, lat))
        seasons = self._needed_seasons()

        stats_by_season = self._load_cached(point, seasons)

        for season in seasons:
            months = stats_by_season.get(season, {})
            if all(month in months for month in self.WINTER_MONTHS):
                continue
            months = self._fetch_season(lat, lon, season)
            for month, stats in months.items():
                self._store_cached(point, season, month, stats)
            stats_by_season[season] = months

        return self._average(stats_by_season, seasons)

    def _load_cached(
        self, point: str, seasons: list[int]
    ) -> dict[int, dict[int, dict[str, float]]]:
        """
        Cached per-month totals for the given point, keyed by season then by
        calendar month.
        """
        placeholders = ",".join("?" * len(seasons))
        query = (
            f"SELECT {CachedWeatherTable.season}, {CachedWeatherTable.month}, "
            f"{CachedWeatherTable.icy_days}, {CachedWeatherTable.rain}, "
            f"{CachedWeatherTable.snow} FROM CachedWeather "
            f"WHERE {CachedWeatherTable.point} = ? "
            f"AND {CachedWeatherTable.season} IN ({placeholders})"
        )
        with cursor(CACHE_DB_PATH, dict_cursor=False) as cur:
            rows = cur.execute(query, (point, *seasons)).fetchall()

        by_season: dict[int, dict[int, dict[str, float]]] = {}
        for season, month, icy_days, rain, snow in rows:
            by_season.setdefault(season, {})[month] = {
                "icy_days": icy_days,
                "rain": rain,
                "snow": snow,
            }
        return by_season

    def _store_cached(
        self, point: str, season: int, month: int, stats: dict[str, float]
    ) -> None:
        """Persist one (point, season, month) row."""
        with cursor(CACHE_DB_PATH, dict_cursor=False) as cur:
            cur.execute(
                f"INSERT OR REPLACE INTO CachedWeather ("
                f"{CachedWeatherTable.point}, {CachedWeatherTable.season}, "
                f"{CachedWeatherTable.month}, {CachedWeatherTable.icy_days}, "
                f"{CachedWeatherTable.rain}, {CachedWeatherTable.snow}"
                f") VALUES (?, ?, ?, ?, ?, ?)",
                (
                    point,
                    season,
                    month,
                    stats["icy_days"],
                    stats["rain"],
                    stats["snow"],
                ),
            )

    def _fetch_season(
        self, lat: float, lon: float, season: int
    ) -> dict[int, dict[str, float]]:
        """
        Fetch one winter (Nov of `season` -> April of `season + 1`) from the
        archive API and reduce it to per-month freeze-thaw / rain / snow totals,
        keyed by calendar month.

        Querying just the winter months -- rather than a multi-year span that
        is half summer -- keeps each call well under the API's daily weight
        budget.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{season}-11-01",
            "end_date": f"{season + 1}-04-30",
            "daily": "temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum",
            "models": "best_match",
            "timezone": self.timezone,
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            return self._month_stats(response.json()["daily"])

        except requests.exceptions.HTTPError:
            if response.status_code == 429:
                if "Daily API request limit exceeded" in response.text:
                    raise ValueError(
                        "Daily API request limit exceeded. Please try again tomorrow."
                    )

                print("Rate limited. Waiting 60 seconds before retry...")
                time.sleep(60)
                return self._fetch_season(lat, lon, season)
            else:
                raise ValueError(
                    f"Weather API call failed with code: {response.status_code}\n{response.text}"
                )
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Weather API request failed: {e!s}")

    def _month_stats(self, data: dict) -> dict[int, dict[str, float]]:
        """
        Reduce one winter's daily records to per-month totals (not averages).

        Every winter month gets an entry -- months with no usable data are
        zeroed rather than omitted, so a fetched season is always complete in
        the cache and never re-fetched.

        Args:
            data: Dict of daily weather records for a single winter

        Returns:
            {month: {"icy_days": int, "rain": float, "snow": float}} for each
            month in WINTER_MONTHS
        """
        # Reshape dict of columns to list of rows
        weather_list = []
        for i in range(len(data["time"])):
            row = {key: data[key][i] for key in data}
            weather_list.append(row)

        # Filter to winter months only and remove incomplete data
        winter_list = self._filter_winter_data(weather_list)

        rows_by_month: dict[int, list[dict]] = {m: [] for m in self.WINTER_MONTHS}
        for row in winter_list:
            month = int(row["time"].split("-")[1])
            rows_by_month[month].append(row)

        return {
            month: {
                "icy_days": self._count_freeze_thaw_days(rows),
                "rain": sum(row["rain_sum"] for row in rows),
                "snow": sum(row["snowfall_sum"] for row in rows),
            }
            for month, rows in rows_by_month.items()
        }

    def _average(
        self,
        stats_by_season: dict[int, dict[int, dict[str, float]]],
        seasons: list[int],
    ) -> dict[str, float]:
        """Average per-month totals over the requested seasons."""
        n = len(seasons)
        totals = {"icy_days": 0.0, "rain": 0.0, "snow": 0.0}
        for season in seasons:
            for month_stats in stats_by_season[season].values():
                for key in totals:
                    totals[key] += month_stats[key]

        return {key: round(value / n, 2) for key, value in totals.items()}

    def _filter_winter_data(self, weather_list: list[dict]) -> list[dict]:
        """
        Filter data to winter months only and remove incomplete records.

        Args:
            weather_list: List of daily weather records

        Returns:
            Filtered list of winter records
        """
        winter_list = []

        for row in weather_list:
            # Parse month from date string (YYYY-MM-DD)
            month = int(row["time"].split("-")[1])

            # Only include winter months
            if month not in self.WINTER_MONTHS:
                continue

            # Skip rows with any None values
            if any(value is None for value in row.values()):
                continue

            winter_list.append(row)

        return winter_list

    def _count_freeze_thaw_days(self, winter_list: list[dict]) -> int:
        """
        Count days with freeze-thaw cycles.

        A freeze-thaw day has:
        - Max temp above freezing (>34°F)
        - Min temp at/below freezing (≤32°F)

        Args:
            winter_list: List of winter weather records

        Returns:
            Number of freeze-thaw days
        """
        freeze_thaw = 0

        for row in winter_list:
            temp_max = float(row["temperature_2m_max"])
            temp_min = float(row["temperature_2m_min"])

            if (
                temp_max > self.FREEZE_THRESHOLD_HIGH
                and temp_min <= self.FREEZE_THRESHOLD_LOW
            ):
                freeze_thaw += 1

        return freeze_thaw

    @staticmethod
    def get_modifier(weather: dict[str, float]) -> float:
        """
        Accepts a dict of averaged winter weather metrics (as returned by
        get()) and returns a modifier between 0-6 degrees based on how a
        resort's weather compares to other resorts. Each metric contributes
        up to 2 degrees: a resort 2 standard deviations harder than the mean
        for a given metric gets the full two points for it.
        """
        icy_days = min(
            max(weather["icy_days"], Weather.MIN_ICY_DAYS), Weather.MAX_ICY_DAYS
        )
        rain = min(weather["rain"], Weather.MAX_RAIN)
        snow = min(weather["snow"], Weather.MAX_SNOW)

        modifier = 0.0

        # Icy days - note the adjustment for both ends of the range being valid
        modifier += (
            (icy_days - Weather.MIN_ICY_DAYS)
            / (Weather.MAX_ICY_DAYS - Weather.MIN_ICY_DAYS)
        ) * 2

        # Rain
        modifier += (rain / Weather.MAX_RAIN) * 2

        # Snow - higher snow means better conditions, so invert the percentage
        modifier += (1 - (snow / Weather.MAX_SNOW)) * 2

        return modifier
