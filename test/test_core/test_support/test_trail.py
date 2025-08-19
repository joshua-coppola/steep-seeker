from shapely import LineString
import pytest

from core.support.trail import Trail
from core.connectors.database import cursor


def test_trail(trail):
    assert trail.geometry == LineString([[1, 1], [0, 0]])


def test_trail_from_db():
    id = "w1000"

    trail = Trail.from_db(id)

    assert trail == "TODO"


def test_trail_to_db(trail, db_path):
    with pytest.raises(Exception) as exc_info:
        trail.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)

    trail.length = 1
    trail.vertical = 1
    trail.difficulty = 1
    trail.max_slope = 1
    trail.average_slope = 1

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Trails"

        result = cur.execute(sql_query).fetchall()

        assert len(result) == 1

        expected_result = {
            "trail_id": "w1000",
            "mountain_id": 1,
            "geometry": "LINESTRING (1 1, 0 0)",
            "name": "Test",
            "official_rating": "Expert",
            "gladed": 1,
            "area": 0,
            "ungroomed": 0,
            "park": 0,
            "length": 1.0,
            "vertical": 1.0,
            "difficulty": 1.0,
            "max_slope": 1.0,
            "average_slope": 1.0,
        }

        assert dict(result[0]) == expected_result
