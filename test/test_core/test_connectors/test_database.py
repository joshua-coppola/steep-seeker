from core.connectors.database import cursor


def test_db_init(db_path: str):
    expected_result = [
        ("Mountains",),
        ("Trails",),
        ("Lifts",),
    ]

    with cursor(db_path=db_path, dict_cursor=False) as cur:
        sql_query = "SELECT name FROM sqlite_master WHERE type='table';"

        assert cur.execute(sql_query).fetchall() == expected_result
