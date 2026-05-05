"""Unit tests for the Weather class."""

import pytest
from unittest.mock import patch, MagicMock
from shapely import Point

from core.connectors.weather_api import Weather


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_row(date: str, t_max: float, t_min: float, rain: float, snow: float) -> dict:
    return {
        "time": date,
        "temperature_2m_max": t_max,
        "temperature_2m_min": t_min,
        "rain_sum": rain,
        "snowfall_sum": snow,
    }


# ---------------------------------------------------------------------------
# _filter_winter_data
# ---------------------------------------------------------------------------


class TestFilterWinterData:
    def setup_method(self):
        self.w = Weather(num_seasons=5)

    def test_keeps_winter_months(self):
        rows = [make_row(f"2023-{m:02d}-15", 30, 20, 0, 1) for m in range(1, 13)]
        result = self.w._filter_winter_data(rows)
        months = {int(r["time"].split("-")[1]) for r in result}
        assert months == set(Weather.WINTER_MONTHS)

    def test_drops_rows_with_none(self):
        rows = [
            make_row("2023-01-10", 30, 20, 0, 1),
            {**make_row("2023-01-11", 30, 20, 0, 1), "rain_sum": None},
        ]
        result = self.w._filter_winter_data(rows)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        assert self.w._filter_winter_data([]) == []


# ---------------------------------------------------------------------------
# _count_freeze_thaw_days
# ---------------------------------------------------------------------------


class TestCountFreezeThawDays:
    def setup_method(self):
        self.w = Weather(num_seasons=5)

    def test_classic_freeze_thaw(self):
        # max > 34, min <= 32 → counts
        rows = [make_row("2023-01-01", 36, 30, 0, 0)]
        assert self.w._count_freeze_thaw_days(rows) == 1

    def test_both_above_freezing_does_not_count(self):
        rows = [make_row("2023-01-01", 40, 35, 0, 0)]
        assert self.w._count_freeze_thaw_days(rows) == 0

    def test_both_below_freezing_does_not_count(self):
        rows = [make_row("2023-01-01", 28, 15, 0, 0)]
        assert self.w._count_freeze_thaw_days(rows) == 0

    def test_boundary_max_exactly_34_does_not_count(self):
        # Condition requires strictly > 34
        rows = [make_row("2023-01-01", 34, 30, 0, 0)]
        assert self.w._count_freeze_thaw_days(rows) == 0

    def test_boundary_min_exactly_32_counts(self):
        # Condition is <= 32, so 32 should count
        rows = [make_row("2023-01-01", 36, 32, 0, 0)]
        assert self.w._count_freeze_thaw_days(rows) == 1

    def test_multiple_rows(self):
        rows = [
            make_row("2023-01-01", 36, 30, 0, 0),  # counts
            make_row("2023-01-02", 40, 35, 0, 0),  # doesn't count
            make_row("2023-01-03", 35, 31, 0, 0),  # counts
        ]
        assert self.w._count_freeze_thaw_days(rows) == 2


# ---------------------------------------------------------------------------
# _process_weather
# ---------------------------------------------------------------------------


class TestProcessWeather:
    def setup_method(self):
        self.w = Weather(num_seasons=2)

    def _make_daily_dict(self, rows):
        keys = [
            "time",
            "temperature_2m_max",
            "temperature_2m_min",
            "rain_sum",
            "snowfall_sum",
        ]
        return {k: [r[k] for r in rows] for k in keys}

    def test_averages_over_num_seasons(self):
        # 2 winter days total, 2 seasons → each metric divided by 2
        rows = [
            make_row("2022-12-01", 36, 30, 0.5, 3.0),
            make_row("2023-01-15", 36, 30, 0.5, 3.0),
        ]
        result = self.w._process_weather(self._make_daily_dict(rows))
        assert result["rain"] == round(1.0 / 2, 2)
        assert result["snow"] == round(6.0 / 2, 2)
        assert result["icy_days"] == round(2 / 2, 2)

    def test_empty_after_filter_returns_zeros(self):
        # Only summer months → filtered out → zeros
        rows = [make_row("2023-07-01", 80, 65, 0.1, 0)]
        result = self.w._process_weather(self._make_daily_dict(rows))
        assert result == {"icy_days": 0, "rain": 0, "snow": 0}


# ---------------------------------------------------------------------------
# get (HTTP layer)
# ---------------------------------------------------------------------------


class TestGet:
    def setup_method(self):
        self.w = Weather(num_seasons=1)

    def _fake_api_response(self):
        return {
            "daily": {
                "time": ["2023-12-01"],
                "temperature_2m_max": [36.0],
                "temperature_2m_min": [30.0],
                "rain_sum": [0.2],
                "snowfall_sum": [4.0],
            }
        }

    @patch("core.connectors.weather_api.requests.get")
    def test_returns_processed_dict(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self._fake_api_response()
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = self.w.get(Point(-72.0, 44.0))
        assert set(result.keys()) == {"icy_days", "rain", "snow"}

    @patch("core.connectors.weather_api.requests.get")
    def test_http_error_raises_value_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = __import__(
            "requests"
        ).exceptions.HTTPError()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="Weather API call failed"):
            self.w.get(Point(-72.0, 44.0))

    @patch("core.connectors.weather_api.requests.get")
    def test_daily_limit_exceeded_raises_value_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Daily API request limit exceeded"
        mock_resp.raise_for_status.side_effect = __import__(
            "requests"
        ).exceptions.HTTPError()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="Daily API request limit exceeded"):
            self.w.get(Point(-72.0, 44.0))
