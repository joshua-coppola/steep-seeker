from datetime import datetime
from uuid import UUID
import pytest

from core.support.mountain import Mountain
from core.datamodels.state import State
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.connectors.database import cursor
from core.datamodels.database import MountainTable


def test_mountain(mountain):
    assert mountain.last_updated.date() == datetime(2000, 2, 5, 12, 30, 5).date()


def test_mountain_region(mountain):
    assert mountain.region() == Region.NORTHEAST


def test_mountain_bearing(mountain):
    assert mountain.bearing() == 180

    mountain.direction = "invalid"

    with pytest.raises(Exception) as exc_info:
        mountain.bearing()

    assert "Invalid direction value:" in exc_info.value.args[0]


def test_mountain_trail_count(mountain):
    assert mountain.trail_count() == 1


def test_mountain_lift_count(mountain):
    assert mountain.lift_count() == 1


def test_mountain_add_trail(mountain, trail):
    trail.trail_id = "w1002"

    mountain.add_trail(trail)
    assert mountain.trail_count() == 2


def test_mountain_from_db(mountain, db_path):
    # TODO: handle trails & lifts getting returned
    mountain.trails = {}
    mountain.lifts = {}
    season_passes = ",".join(
        [season_pass.value for season_pass in mountain.season_passes]
    )

    with cursor(db_path=db_path) as cur:
        query = f"""
            INSERT INTO Mountains (
                {MountainTable.mountain_id},
                {MountainTable.name},
                {MountainTable.state},
                {MountainTable.direction},
                {MountainTable.coordinates},
                {MountainTable.season_passes},
                {MountainTable.vertical},
                {MountainTable.difficulty},
                {MountainTable.beginner_friendliness},
                {MountainTable.average_icy_days},
                {MountainTable.average_snow},
                {MountainTable.average_rain},
                {MountainTable.last_updated},
                {MountainTable.url}
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            mountain.mountain_id,
            mountain.name,
            mountain.state.value,
            mountain.direction,
            str(mountain.coordinates),
            season_passes,
            mountain.vertical,
            mountain.difficulty,
            mountain.beginner_friendliness,
            mountain.average_icy_days,
            mountain.average_snow,
            mountain.average_rain,
            mountain.last_updated,
            mountain.url,
        )
        cur.execute(query, params)

    returned_mountain = Mountain.from_db(mountain.mountain_id, db_path)

    assert returned_mountain == mountain


def test_mountain_to_db(mountain, db_path):
    mountain.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Mountains"

        result = cur.execute(sql_query).fetchall()

        assert len(result) == 1

        expected_result = {
            "mountain_id": 1,
            "name": "Test",
            "state": "VT",
            "direction": "n",
            "coordinates": "POINT (1 1)",
            "season_passes": "Epic,Ikon",
            "vertical": 1024,
            "difficulty": 89.0,
            "beginner_friendliness": 1.0,
            "average_icy_days": 25.0,
            "average_snow": 150.0,
            "average_rain": 10.0,
            "last_updated": str(datetime(2000, 2, 5, 12, 30, 5)),
            "url": "https://test.com",
        }

        assert dict(result[0]) == expected_result

    mountain.name = None

    with pytest.raises(Exception) as exc_info:
        mountain.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)


def test_mountain_from_osm(osm_file):
    season_passes = [Season_Pass.EPIC, Season_Pass.IKON]
    mountain = Mountain.from_osm(osm_file, season_passes)

    assert mountain.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")
    assert mountain.name == "test"
    assert mountain.state == State("VT")
    assert mountain.direction == "w"
    assert mountain.season_passes == season_passes
