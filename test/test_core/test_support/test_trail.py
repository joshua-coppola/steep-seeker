from shapely import LineString
import pytest

from core.support.trail import Trail
from core.connectors.database import cursor
from core.datamodels.database import TrailTable


def test_trail(trail):
    assert trail.geometry == LineString([[1, 1], [0, 0]])


def test_trail_from_db(trail, db_path):
    with cursor(db_path=db_path) as cur:
        query = f"""
            INSERT INTO Trails (
                {TrailTable.trail_id},
                {TrailTable.mountain_id},
                {TrailTable.geometry},
                {TrailTable.name},
                {TrailTable.official_rating},
                {TrailTable.gladed},
                {TrailTable.area},
                {TrailTable.ungroomed},
                {TrailTable.park},
                {TrailTable.length},
                {TrailTable.vertical},
                {TrailTable.difficulty},
                {TrailTable.max_slope},
                {TrailTable.average_slope}
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            trail.trail_id,
            trail.mountain_id,
            str(trail.geometry),
            trail.name,
            trail.official_rating,
            trail.gladed,
            trail.area,
            trail.ungroomed,
            trail.park,
            trail.length,
            trail.vertical,
            trail.difficulty,
            trail.max_slope,
            trail.average_slope,
        )
        cur.execute(query, params)

    returned_trail = Trail.from_db(trail.trail_id, db_path=db_path)

    assert trail == returned_trail

    assert Trail.from_db("fake_id", db_path) is None


def test_trail_to_db(trail, db_path):
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

    trail.name = None

    with pytest.raises(Exception) as exc_info:
        trail.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)
