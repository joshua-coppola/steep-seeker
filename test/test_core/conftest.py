import pytest

from core.connectors.database import db_init, DATABASE_INIT_SQL


@pytest.fixture
def osm_file():
    return "test/test_core/test_osm/test.osm"


@pytest.fixture
def db_path(tmpdir):
    db_path = tmpdir + "/db.db"

    open(db_path, "w").close()

    db_init(db_path=db_path, sql_path=DATABASE_INIT_SQL)

    return db_path


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
        """Mock elevation API - adds elevation of 1500 to each coordinate"""
        return [[lon, lat, 1500.0] for lon, lat in nodes]
