import sqlite3
from contextlib import contextmanager

DATABASE_PATH = "data/new_db.db"
DATABASE_INIT_SQL = "config/new_db.sql"

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


def db_init(db_path: str = DATABASE_PATH, sql_path: str = DATABASE_INIT_SQL) -> None:
    """
    Reads in SQL from sql_path and uses it to reinitialze the database specified by db_path
    """
    with open(sql_path) as f:
        with cursor(db_path) as cur:
            cur.executescript(f.read())
