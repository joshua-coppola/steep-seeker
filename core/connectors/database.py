import sqlite3
import uuid
from contextlib import contextmanager

DATABASE_PATH = "data/db.db"
DATABASE_INIT_SQL = "config/db.sql"

CACHE_DB_PATH = "data/cache_db.db"
CACHE_DB_INIT_SQL = "config/cache_db.sql"


@contextmanager
def cursor(db_path: str = DATABASE_PATH, dict_cursor: bool = True):
    """
    Creates SQLite connection for the given db_path and ensures
    commit & close after use.
    """
    conn = sqlite3.connect(db_path)
    if dict_cursor:
        conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def db_id(value):
    """
    Normalizes a mountain_id for use as a SQL bind parameter: sqlite3 can't
    bind a uuid.UUID directly (OSM-derived mountain_ids are UUID3s), so
    those become str and everything else passes through unchanged.
    """
    return str(value) if isinstance(value, uuid.UUID) else value


def db_init(db_path: str = DATABASE_PATH, sql_path: str = DATABASE_INIT_SQL) -> None:
    """
    Reads in SQL from sql_path and uses it to reinitialze the database specified by db_path
    """
    with open(sql_path) as f, cursor(db_path) as cur:
        cur.executescript(f.read())
