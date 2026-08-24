import time
from datetime import datetime, timezone
from typing import ClassVar

import requests
from shapely import Point


class Weather:
    """Fetches and processes historical weather data for ski season analysis."""

    # Class constants
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    WINTER_MONTHS: ClassVar[list[int]] = [11, 12, 1, 2, 3, 4]  # Nov - April
    FREEZE_THRESHOLD_HIGH = 34  # °F
    FREEZE_THRESHOLD_LOW = 32  # °F

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

    def _get_date_range(self) -> tuple[str, str]:
        """Calculate dynamic date range based on current date and num_seasons."""
        end_date = datetime.now(timezone.utc)

        # If we're past April, use this year's April 30, else use last year's
        if end_date.month > self.WINTER_MONTHS[-1]:
            end_date = datetime(
                end_date.year, self.WINTER_MONTHS[-1], 30, tzinfo=timezone.utc
            )
        else:
            end_date = datetime(
                end_date.year - 1, self.WINTER_MONTHS[-1], 30, tzinfo=timezone.utc
            )

        # Start date is num_seasons years before, November 1
        start_date = datetime(
            end_date.year - self.num_seasons, 11, 1, tzinfo=timezone.utc
        )

        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def get(self, coordinate: Point) -> dict[str, float]:
        """
        Fetch and process historical weather data for a location.

        Args:
            coordinate: Shapely point containing a lat/lon

        Returns:
            Dictionary with averaged winter weather metrics:
                - icy_days: Average freeze-thaw days per season
                - rain: Average rain total per season (inches)
                - snow: Average snowfall per season (inches)
        """
        start_date, end_date = self._get_date_range()

        params = {
            "latitude": coordinate.y,
            "longitude": coordinate.x,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum",
            "models": "best_match",
            "timezone": self.timezone,
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()["daily"]
            return self._process_weather(data)

        except requests.exceptions.HTTPError:
            if response.status_code == 429:
                if "Daily API request limit exceeded" in response.text:
                    raise ValueError(
                        "Daily API request limit exceeded. Please try again tomorrow."
                    )

                print("Rate limited. Waiting 60 seconds before retry...")
                time.sleep(60)
                return self.get(coordinate)
            else:
                raise ValueError(
                    f"Weather API call failed with code: {response.status_code}\n{response.text}"
                )
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Weather API request failed: {e!s}")

    def _process_weather(self, data: dict) -> dict[str, float]:
        """
        Process daily weather data into seasonal averages.

        Args:
            data: Dict of daily weather records

        Returns:
            Dictionary with averaged metrics
        """
        # Reshape dict to list
        weather_list = []
        for i in range(len(data["time"])):
            row = {key: data[key][i] for key in data}
            weather_list.append(row)

        # Filter to winter months only and remove incomplete data
        winter_list = self._filter_winter_data(weather_list)

        if not winter_list:
            return {"icy_days": 0, "rain": 0, "snow": 0}

        # Calculate metrics
        freeze_thaw_days = self._count_freeze_thaw_days(winter_list)
        rain_total = sum(row["rain_sum"] for row in winter_list)
        snow_total = sum(row["snowfall_sum"] for row in winter_list)

        # Average over seasons
        return {
            "icy_days": round(freeze_thaw_days / self.num_seasons, 2),
            "rain": round(rain_total / self.num_seasons, 2),
            "snow": round(snow_total / self.num_seasons, 2),
        }

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
