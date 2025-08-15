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
