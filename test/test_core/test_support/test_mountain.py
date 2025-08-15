from datetime import datetime
from uuid import UUID
import pytest

from core.support.mountain import Mountain
from core.datamodels.state import State
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.connectors.database import cursor


def test_mountain(mountain):
    assert mountain.last_updated.date() == datetime.now().date()


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
    trail.id = "w1002"

    mountain.add_trail(trail)
    assert mountain.trail_count() == 2


def test_mountain_from_db():
    id = "w1000"

    mountain = Mountain.from_db(id)

    assert mountain == "TODO"


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
            "season_passes": None,
            "vertical": None,
            "difficulty": None,
            "beginner_friendliness": None,
            "average_icy_days": None,
            "average_snow": None,
            "average_rain": None,
            "last_updated": None,
            "url": None,
        }

        assert dict(result[0]) == expected_result

    mountain.name = None

    with pytest.raises(Exception) as exc_info:
        mountain.to_db()

    assert "fields are missing" in str(exc_info)


def test_mountain_from_osm(osm_file):
    season_passes = [Season_Pass.EPIC, Season_Pass.IKON]
    mountain = Mountain.from_osm(osm_file, season_passes)

    assert mountain.id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")
    assert mountain.name == "test"
    assert mountain.state == State("VT")
    assert mountain.direction == "w"
    assert mountain.season_passes == season_passes
