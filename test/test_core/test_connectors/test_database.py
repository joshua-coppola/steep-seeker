from core.connectors.database import db_init, cursor, DATABASE_INIT_SQL


def test_db_init(tmpdir):
    db_path = tmpdir + "/db.db"

    open(db_path, "w").close()

    db_init(db_path, DATABASE_INIT_SQL)

    expected_result = [
        ("Mountains",),
        ("Trails",),
        ("Lifts",),
        ("TrailPoints",),
        ("LiftPoints",),
        ("CachedPoints",),
    ]

    with cursor(db_path=db_path, dict_cursor=False) as cur:
        sql_query = "SELECT name FROM sqlite_master WHERE type='table';"

        assert cur.execute(sql_query).fetchall() == expected_result
