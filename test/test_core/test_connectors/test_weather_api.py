"""Unit tests for the Weather class."""

from unittest.mock import MagicMock, patch

import pytest
from shapely import Point

from core.connectors import weather_api
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
# _month_stats
# ---------------------------------------------------------------------------


class TestMonthStats:
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

    def test_totals_are_bucketed_by_month(self):
        # _month_stats sums each winter month separately; averaging over
        # seasons happens later in _average
        rows = [
            make_row("2022-12-01", 36, 30, 0.5, 3.0),
            make_row("2022-12-20", 36, 30, 0.5, 3.0),
            make_row("2023-01-15", 36, 30, 0.4, 2.0),
        ]
        result = self.w._month_stats(self._make_daily_dict(rows))

        assert result[12] == {"icy_days": 2, "rain": 1.0, "snow": 6.0}
        assert result[1] == {"icy_days": 1, "rain": 0.4, "snow": 2.0}

    def test_every_winter_month_present_even_when_empty(self):
        rows = [make_row("2023-01-15", 36, 30, 0.4, 2.0)]
        result = self.w._month_stats(self._make_daily_dict(rows))

        assert set(result) == set(Weather.WINTER_MONTHS)
        assert result[11] == {"icy_days": 0, "rain": 0, "snow": 0}

    def test_summer_only_input_yields_all_zero_months(self):
        rows = [make_row("2023-07-01", 80, 65, 0.1, 0)]
        result = self.w._month_stats(self._make_daily_dict(rows))
        assert all(m == {"icy_days": 0, "rain": 0, "snow": 0} for m in result.values())


# ---------------------------------------------------------------------------
# _needed_seasons / _average
# ---------------------------------------------------------------------------


class TestNeededSeasons:
    def test_returns_num_seasons_consecutive_completed_winters(self):
        seasons = Weather(num_seasons=5)._needed_seasons()
        assert len(seasons) == 5
        assert seasons == sorted(seasons)
        assert seasons[-1] - seasons[0] == 4

    def test_latest_season_is_a_completed_winter(self):
        # The most recent season must have finished (we are past its April).
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        latest = Weather()._latest_season()
        # Winter `latest` ends in April of latest + 1; that April is in the past.
        assert (latest + 1, 4) <= (now.year, now.month)


class TestAverage:
    def test_sums_months_within_season_then_divides_by_season_count(self):
        w = Weather(num_seasons=2)
        stats = {
            2022: {
                12: {"icy_days": 6, "rain": 1.5, "snow": 25.0},
                1: {"icy_days": 4, "rain": 0.5, "snow": 15.0},
            },
            2023: {
                12: {"icy_days": 12, "rain": 3.0, "snow": 40.0},
                1: {"icy_days": 8, "rain": 1.0, "snow": 20.0},
            },
        }
        result = w._average(stats, [2022, 2023])
        # per-season totals: 2022 -> (10, 2.0, 40.0), 2023 -> (20, 4.0, 60.0)
        assert result == {"icy_days": 15.0, "rain": 3.0, "snow": 50.0}


# ---------------------------------------------------------------------------
# get (HTTP layer)
# ---------------------------------------------------------------------------


def _daily_payload(*, rain=0.2, snow=4.0):
    return {
        "daily": {
            "time": ["2023-12-01"],
            "temperature_2m_max": [36.0],
            "temperature_2m_min": [30.0],
            "rain_sum": [rain],
            "snowfall_sum": [snow],
        }
    }


class TestGet:
    @pytest.fixture(autouse=True)
    def _cache(self, monkeypatch, cache_db_path):
        monkeypatch.setattr(weather_api, "CACHE_DB_PATH", cache_db_path)

    @patch("core.connectors.weather_api.requests.get")
    def test_returns_averaged_dict(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _daily_payload()
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = Weather(num_seasons=3).get(Point(-72.0, 44.0))
        assert set(result.keys()) == {"icy_days", "rain", "snow"}

    @patch("core.connectors.weather_api.requests.get")
    def test_one_api_call_per_needed_season(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _daily_payload()
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        Weather(num_seasons=4).get(Point(-72.0, 44.0))
        assert mock_get.call_count == 4

    @patch("core.connectors.weather_api.requests.get")
    def test_second_call_is_served_from_cache(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _daily_payload()
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        first = Weather(num_seasons=3).get(Point(-72.0, 44.0))
        calls_after_first = mock_get.call_count

        # Float noise past the 6th decimal rounds to the same cached point.
        second = Weather(num_seasons=3).get(Point(-72.0 + 3e-9, 44.0 - 4e-9))

        assert mock_get.call_count == calls_after_first  # no new API calls
        assert second == first

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
            Weather(num_seasons=1).get(Point(-72.0, 44.0))

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
            Weather(num_seasons=1).get(Point(-72.0, 44.0))


# ---------------------------------------------------------------------------
# Weather.get_modifier
# ---------------------------------------------------------------------------


class TestGetModifier:
    def test_calmest_conditions_give_minimum_modifier(self):
        # No rain, no icy days, and max snow (best possible conditions) -> 0
        modifier = Weather.get_modifier({"icy_days": 2.5, "rain": 0, "snow": 202.44})
        assert modifier == 0

    def test_no_snow_still_gives_partial_modifier(self):
        # Zero snow is worse than average, but icy_days/rain are still at
        # their minimum, so only the snow component contributes
        modifier = Weather.get_modifier({"icy_days": 2.5, "rain": 0, "snow": 0})
        assert modifier == 2.0

    def test_harshest_conditions_give_maximum_modifier(self):
        modifier = Weather.get_modifier({"icy_days": 100, "rain": 20, "snow": 0})
        assert modifier == 6.0

    def test_out_of_range_values_are_clamped(self):
        # icy_days/rain far above their max should clamp to the same
        # result as the harshest-conditions case
        clamped = Weather.get_modifier({"icy_days": 1000, "rain": 1000, "snow": 0})
        assert clamped == 6.0

    def test_typical_conditions(self):
        modifier = Weather.get_modifier(
            {"icy_days": 50.1, "rain": 10.01, "snow": 125.00}
        )
        assert round(modifier, 4) == 3.4627
