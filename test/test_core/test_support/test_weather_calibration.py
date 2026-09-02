"""Unit tests for WeatherCalibration and recalibrate."""

import json

import pytest

from core.connectors.database import cursor
from core.datamodels.database import MountainTable
from core.support.mountain import Mountain
from core.support.weather_calibration import (
    DEFAULT_CALIBRATION_PATH,
    WeatherCalibration,
    recalibrate,
)


def _calibration(icy=None, rain=None, snow=None):
    return WeatherCalibration(
        icy_days=icy or [0.0, 20.0, 40.0, 60.0, 80.0],
        rain=rain or [0.0, 5.0, 10.0, 15.0, 20.0],
        snow=snow or [0.0, 50.0, 100.0, 150.0, 200.0],
        n_resorts=5,
        created="2024-01-01T00:00:00+00:00",
    )


class TestFromPopulation:
    def test_sorts_each_metric(self):
        calib = WeatherCalibration.from_population(
            [(40, 8, 100), (10, 2, 300), (25, 5, 50)]
        )
        assert calib.icy_days == [10.0, 25.0, 40.0]
        assert calib.rain == [2.0, 5.0, 8.0]
        assert calib.snow == [50.0, 100.0, 300.0]
        assert calib.n_resorts == 3

    def test_empty_population_raises(self):
        with pytest.raises(ValueError, match="empty population"):
            WeatherCalibration.from_population([])


class TestRank:
    def test_at_or_below_minimum_is_zero(self):
        assert WeatherCalibration._rank([10.0, 20.0, 30.0], 10.0) == 0.0
        assert WeatherCalibration._rank([10.0, 20.0, 30.0], 5.0) == 0.0

    def test_at_or_above_maximum_is_one(self):
        assert WeatherCalibration._rank([10.0, 20.0, 30.0], 30.0) == 1.0
        assert WeatherCalibration._rank([10.0, 20.0, 30.0], 99.0) == 1.0

    def test_interpolates_between_neighbours(self):
        # three-quarters of the way to the top of a 3-value list: (1 + 0.5) / 2
        assert WeatherCalibration._rank([0.0, 10.0, 20.0], 15.0) == 0.75

    def test_handles_tied_values(self):
        assert WeatherCalibration._rank([0.0, 10.0, 10.0, 20.0], 10.0) == pytest.approx(
            1 / 3
        )


class TestModifier:
    def test_calmest_conditions_give_zero(self):
        assert _calibration().modifier({"icy_days": 0, "rain": 0, "snow": 200}) == 0.0

    def test_harshest_conditions_give_six(self):
        assert _calibration().modifier({"icy_days": 80, "rain": 20, "snow": 0}) == 6.0

    def test_out_of_range_values_saturate(self):
        assert _calibration().modifier({"icy_days": 999, "rain": 999, "snow": 0}) == 6.0

    def test_snow_is_inverted(self):
        calib = _calibration()
        # median icy/rain (1.0 each); max snow -> snow contributes 0
        assert calib.modifier({"icy_days": 40, "rain": 10, "snow": 200}) == 2.0
        # ... and no snow -> snow contributes the full 2
        assert calib.modifier({"icy_days": 40, "rain": 10, "snow": 0}) == 4.0


class TestPersistence:
    def test_json_round_trip(self):
        calib = _calibration()
        assert WeatherCalibration.from_json(calib.to_json()) == calib

    def test_save_then_load(self, db_path):
        _calibration(icy=[1.0, 2.0, 3.0]).save(db_path)
        loaded = WeatherCalibration.load(db_path)
        assert loaded.icy_days == [1.0, 2.0, 3.0]
        assert loaded.n_resorts == 5

    def test_load_falls_back_to_bootstrap_snapshot(self, db_path):
        with cursor(db_path) as cur:
            cur.execute("DELETE FROM WeatherCalibration")

        with open(DEFAULT_CALIBRATION_PATH) as f:
            shipped = WeatherCalibration.from_json(f.read())
        assert WeatherCalibration.load(db_path) == shipped

    def test_bootstrap_snapshot_is_well_formed(self):
        with open(DEFAULT_CALIBRATION_PATH) as f:
            data = json.load(f)
        assert set(data) == {"icy_days", "rain", "snow", "n_resorts", "created"}
        assert data["n_resorts"] == len(data["icy_days"]) > 0
        assert data["icy_days"] == sorted(data["icy_days"])


class TestRecalibrate:
    def test_rebuilds_calibration_and_rerates_trails(
        self, db_path, mountain_factory, trail_factory
    ):
        mountain_factory(
            mountain_id="a",
            name="Alpha",
            average_icy_days=10.0,
            average_rain=2.0,
            average_snow=200.0,
            trails={
                "w1": trail_factory(
                    trail_id="w1",
                    mountain_id="a",
                    gladed=False,
                    ungroomed=False,
                    steepest_30m=20.0,
                    difficulty=99.0,  # stale, should be overwritten
                    length=200,
                )
            },
        ).to_db(db_path)
        mountain_factory(
            mountain_id="b",
            name="Beta",
            average_icy_days=90.0,
            average_rain=12.0,
            average_snow=10.0,
            trails={
                "w2": trail_factory(
                    trail_id="w2",
                    mountain_id="b",
                    gladed=False,
                    ungroomed=False,
                    steepest_30m=20.0,
                    difficulty=99.0,
                    length=200,
                )
            },
        ).to_db(db_path)

        summary = recalibrate(db_path)

        assert summary["n_resorts"] == 2
        assert summary["n_trails_rerated"] == 2
        assert sorted(summary["rerated_mountain_ids"]) == ["a", "b"]

        calib = WeatherCalibration.load(db_path)
        assert calib.n_resorts == 2
        assert calib.icy_days == [10.0, 90.0]

        # Alpha holds the population-min weather -> modifier 0 -> difficulty == pitch
        alpha = Mountain.from_db("a", db_path=db_path)
        assert alpha.trails["w1"].difficulty == 20.0
        # Beta holds the population-max weather -> modifier 6 -> pitch + 6
        beta = Mountain.from_db("b", db_path=db_path)
        assert beta.trails["w2"].difficulty == 26.0

    def test_skips_mountains_without_weather(self, db_path, mountain_factory):
        mountain_factory(
            mountain_id="a",
            name="Alpha",
            average_icy_days=30.0,
            average_rain=5.0,
            average_snow=80.0,
        ).to_db(db_path)
        mountain_factory(mountain_id="b", name="Beta").to_db(db_path)
        with cursor(db_path) as cur:
            cur.execute(
                f"""
                UPDATE Mountains SET
                    {MountainTable.average_icy_days} = NULL,
                    {MountainTable.average_rain} = NULL,
                    {MountainTable.average_snow} = NULL
                WHERE {MountainTable.mountain_id} = 'b'
                """
            )

        assert recalibrate(db_path)["n_resorts"] == 1
