from datetime import UTC, datetime

import pytest
from shapely import LineString, Point

from core.connectors.database import CACHE_DB_INIT_SQL, DATABASE_INIT_SQL, db_init
from core.connectors.weather_api import Weather
from core.datamodels.database import LiftTable, MountainTable, TrailTable
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.lift import Lift
from core.support.mountain import Mountain
from core.support.trail import Trail


@pytest.fixture
def osm_file():
    return "test/test_core/test_osm/test.osm"


@pytest.fixture
def db_path(tmpdir):
    db_path = tmpdir + "/db.db"

    open(db_path, "w").close()

    db_init(db_path=db_path, sql_path=DATABASE_INIT_SQL)

    return db_path


@pytest.fixture
def cache_db_path(tmpdir):
    cache_db_path = tmpdir + "/cache_db.db"

    open(cache_db_path, "w").close()

    db_init(db_path=cache_db_path, sql_path=CACHE_DB_INIT_SQL)

    return cache_db_path


class FakeResponse:
    def __init__(self, status_code=200, results=None):
        self.status_code = status_code
        self._results = results or []
        self.text = "fake response"

    def json(self):
        return {"results": self._results}


class FakeElevation:
    last_called = 0.0

    def __init__(self):
        pass

    def get(self, nodes, spacing=100):
        """Mock elevation API - returns a descending elevation profile per
        segment, starting at 1500 and dropping by 1 for each new point
        processed in this call. A point whose lon/lat was already seen in
        this call (e.g. a polygon ring's closing point) gets the same
        elevation as when it was first seen, matching how the real
        elevation API/cache treats identical coordinates."""
        seen = {}
        results = []
        for lon, lat in nodes:
            key = (round(lon, 6), round(lat, 6))
            if key not in seen:
                seen[key] = 1500.0 - len(seen)
            results.append([key[0], key[1], seen[key]])
        return results


class FakeWeather(Weather):
    def get(self, coordinates: Point):
        return {"icy_days": 50.1, "rain": 10.01, "snow": 125.00}


@pytest.fixture
def trail_factory():
    def _make_trail(**overrides):
        trail_dict = {
            TrailTable.trail_id: "w1000",
            TrailTable.mountain_id: "1",
            TrailTable.geometry: LineString(
                [[1, 1, 10], [0, 0, 0]]
            ),  # lon, lat, elevation
            TrailTable.interior_geometry: LineString([[1, 1, 10], [0, 0, 0]]),
            TrailTable.name: "Test",
            TrailTable.official_rating: "Expert",
            TrailTable.gladed: True,
            TrailTable.area: False,
            TrailTable.ungroomed: False,
            TrailTable.park: False,
            TrailTable.length: 1,
            TrailTable.vertical: 1,
            TrailTable.difficulty: 1.0,
            TrailTable.max_slope: 1.0,
            TrailTable.average_slope: 1.0,
            TrailTable.steepest_30m: 1.0,
            TrailTable.steepest_50m: 1.0,
            TrailTable.steepest_100m: 1.0,
            TrailTable.steepest_200m: 1.0,
            TrailTable.steepest_500m: 1.0,
            TrailTable.steepest_1000m: 1.0,
        }
        trail_dict.update(overrides)
        return Trail(**trail_dict)

    return _make_trail


@pytest.fixture
def lift_factory():
    def _make_lift(**overrides):
        lift_dict = {
            LiftTable.lift_id: "w1001",
            LiftTable.mountain_id: "1",
            LiftTable.geometry: LineString([[1, 1, 10], [0, 0, 0]]),
            LiftTable.name: "Test",
            LiftTable.lift_type: "chair_lift",
            LiftTable.occupancy: 4,
            LiftTable.capacity: 1200,
            LiftTable.detachable: False,
            LiftTable.bubble: False,
            LiftTable.heating: False,
            LiftTable.length: 1,
            LiftTable.vertical: 1,
            LiftTable.average_slope: 1.0,
        }
        lift_dict.update(overrides)
        return Lift(**lift_dict)

    return _make_lift


@pytest.fixture
def mountain_factory(trail_factory, lift_factory):
    def _make_mountain(**overrides):
        mountain_id = overrides.get(MountainTable.mountain_id, "1")
        trails = overrides.pop("trails", None)
        lifts = overrides.pop("lifts", None)

        if trails is None:
            default_trail = trail_factory(**{TrailTable.mountain_id: mountain_id})
            trails = {default_trail.trail_id: default_trail}
        if lifts is None:
            default_lift = lift_factory(**{LiftTable.mountain_id: mountain_id})
            lifts = {default_lift.lift_id: default_lift}

        mountain_dict = {
            MountainTable.mountain_id: "1",
            MountainTable.name: "Test",
            MountainTable.state: State.VERMONT,
            MountainTable.direction: "n",
            MountainTable.coordinates: Point(1, 1),
            MountainTable.season_passes: [Season_Pass.EPIC, Season_Pass.IKON],
            MountainTable.url: "https://test.com",
            MountainTable.vertical: 1024,
            MountainTable.difficulty: 89,
            MountainTable.beginner_friendliness: 1,
            MountainTable.average_icy_days: 25,
            MountainTable.average_snow: 150,
            MountainTable.average_rain: 10,
            MountainTable.trails: trails,
            MountainTable.lifts: lifts,
            MountainTable.last_updated: datetime(2000, 2, 5, 12, 30, 5, tzinfo=UTC),
        }
        mountain_dict.update(overrides)
        return Mountain(**mountain_dict)

    return _make_mountain
