import pytest
from shapely import Point

from core.connectors.database import CACHE_DB_INIT_SQL, DATABASE_INIT_SQL, db_init
from core.connectors.weather_api import Weather


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
            key = (lon, lat)
            if key not in seen:
                seen[key] = 1500.0 - len(seen)
            results.append([lon, lat, seen[key]])
        return results


class FakeWeather(Weather):
    def get(self, coordinates: Point):
        return {"icy_days": 50.1, "rain": 10.01, "snow": 125.00}
