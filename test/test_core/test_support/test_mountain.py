from datetime import datetime, timezone
from uuid import UUID

import pytest
from shapely import Point

from core.connectors.database import cursor
from core.datamodels.database import LiftTable, MountainTable, TrailTable
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.osm import osm_processor
from core.support import mountain as mountain_module
from core.support.mountain import Mountain
from test.test_core.conftest import FakeElevation, FakeWeather


def test_mountain(mountain_factory):
    mountain = mountain_factory()
    expected = datetime(2000, 2, 5, 12, 30, 5, tzinfo=timezone.utc)
    assert mountain.last_updated.date() == expected.date()


def test_mountain_region(mountain_factory):
    mountain = mountain_factory()
    assert mountain.region() == Region.NORTHEAST


def test_mountain_vertical_feet(mountain_factory):
    mountain = mountain_factory(vertical=1024)
    assert mountain.vertical_feet() == round(1024 * 3.28084)


def test_mountain_bearing(mountain_factory):
    mountain = mountain_factory()
    assert mountain.bearing() == 180

    mountain.direction = "invalid"

    with pytest.raises(Exception) as exc_info:
        mountain.bearing()

    assert "Invalid direction value:" in exc_info.value.args[0]


def test_mountain_trail_count(mountain_factory):
    mountain = mountain_factory()
    assert mountain.trail_count() == 1


def test_mountain_lift_count(mountain_factory):
    mountain = mountain_factory()
    assert mountain.lift_count() == 1


def test_mountain_add_trail(mountain_factory, trail_factory):
    mountain = mountain_factory()
    trail = trail_factory(trail_id="w1002")

    mountain.add_trail(trail)
    assert mountain.trail_count() == 2


def test_mountain_from_db(mountain_factory, db_path):
    mountain = mountain_factory()
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
            mountain.last_updated.isoformat(),
            mountain.url,
        )
        cur.execute(query, params)

    for trail_id in mountain.trails:
        mountain.trails[trail_id].to_db(db_path)

    for lift_id in mountain.lifts:
        mountain.lifts[lift_id].to_db(db_path)

    returned_mountain = Mountain.from_db(mountain.mountain_id, db_path)

    assert returned_mountain == mountain

    assert Mountain.from_db("fake_id", db_path) is None


def test_mountain_from_name(mountain_factory, db_path):
    mountain = mountain_factory()
    mountain.to_db(db_path=db_path)

    returned_mountain = Mountain.from_name(mountain.name, mountain.state, db_path)

    assert returned_mountain == mountain


def test_mountain_from_name_no_match_returns_none(db_path):
    assert Mountain.from_name("Nonexistent", State.VERMONT, db_path) is None


def test_mountain_from_db_handles_empty_season_passes(mountain_factory, db_path):
    # to_db stores an empty season_passes list as "" (",".join([]) == "");
    # from_db must not try to build a Season_Pass("") out of that
    mountain = mountain_factory(season_passes=[])
    mountain.to_db(db_path=db_path)

    returned_mountain = Mountain.from_db(mountain.mountain_id, db_path)

    assert returned_mountain.season_passes == []


def test_mountain_to_db(mountain_factory, db_path):
    mountain = mountain_factory()
    mountain.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Mountains"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1

    expected_result = {
        MountainTable.mountain_id: "1",
        MountainTable.name: "Test",
        MountainTable.state: "VT",
        MountainTable.direction: "n",
        MountainTable.coordinates: "POINT (1 1)",
        MountainTable.season_passes: "Epic,Ikon",
        MountainTable.vertical: 1024,
        MountainTable.difficulty: 89.0,
        MountainTable.beginner_friendliness: 1.0,
        MountainTable.average_icy_days: 25.0,
        MountainTable.average_snow: 150.0,
        MountainTable.average_rain: 10.0,
        MountainTable.last_updated: datetime(
            2000, 2, 5, 12, 30, 5, tzinfo=timezone.utc
        ).isoformat(),
        MountainTable.url: "https://test.com",
    }

    assert dict(result[0]) == expected_result

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = f"SELECT * FROM Trails WHERE {MountainTable.mountain_id} = ?"
        params = (expected_result[MountainTable.mountain_id],)
        trail_result = cur.execute(sql_query, params).fetchall()

    assert len(trail_result) == 1

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = f"SELECT * FROM Lifts WHERE {MountainTable.mountain_id} = ?"
        params = (expected_result[MountainTable.mountain_id],)
        lift_result = cur.execute(sql_query, params).fetchall()

    assert len(lift_result) == 1

    mountain.vertical = 2048
    expected_result[MountainTable.vertical] = 2048

    mountain.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Mountains"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1
    assert dict(result[0]) == expected_result

    mountain.name = None

    with pytest.raises(Exception) as exc_info:
        mountain.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)


def test_mountain_to_db_rounds_coordinates_precision(mountain_factory, db_path):
    mountain = mountain_factory()
    mountain.coordinates = Point(-72.1234567891, 43.1234567891)

    mountain.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = dict(cur.execute("SELECT * FROM Mountains").fetchall()[0])

    assert result[MountainTable.coordinates] == "POINT (-72.123457 43.123457)"


def test_mountain_to_db_serializes_uuid_mountain_id(mountain_factory, db_path):
    # OSMProcessor generates mountain_id as a uuid.UUID when one isn't
    # supplied; sqlite3 can't bind UUID objects directly, so to_db (and the
    # Trail/Lift to_db calls it cascades into via the mountain_id foreign
    # key) must convert it to a string before saving.
    mountain_id = UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")
    mountain = mountain_factory(mountain_id=mountain_id)

    mountain.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        mountain_result = dict(cur.execute("SELECT * FROM Mountains").fetchall()[0])
        trail_result = dict(cur.execute("SELECT * FROM Trails").fetchall()[0])
        lift_result = dict(cur.execute("SELECT * FROM Lifts").fetchall()[0])

    assert mountain_result[MountainTable.mountain_id] == str(mountain_id)
    assert trail_result[TrailTable.mountain_id] == str(mountain_id)
    assert lift_result[LiftTable.mountain_id] == str(mountain_id)

    # from_db's WHERE lookup must also accept a UUID param directly
    returned_mountain = Mountain.from_db(mountain_id, db_path)
    assert returned_mountain.mountain_id == str(mountain_id)


def test_mountain_from_osm(osm_file, monkeypatch):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)
    monkeypatch.setattr(mountain_module, "Weather", FakeWeather)

    season_passes = [Season_Pass.EPIC, Season_Pass.IKON]
    url = "https://test.com"
    mountain = Mountain.from_osm(osm_file, season_passes, url)

    assert mountain.mountain_id == UUID("9dbdb8fe-1bea-3fa8-9505-18f2171c4f50")
    assert mountain.name == "test"
    assert mountain.state == State("VT")
    assert mountain.direction == "w"
    assert mountain.coordinates.x == pytest.approx(-72.73645, abs=1e-5)
    assert mountain.coordinates.y == pytest.approx(43.41029, abs=1e-5)
    assert mountain.season_passes == season_passes
    assert mountain.url == url
    # FakeElevation descends 1 unit per point within each trail/area segment;
    # the mountain's vertical is the max-min elevation across all trail points
    assert mountain.vertical == 1215
    assert mountain.difficulty == 18.3
    assert mountain.beginner_friendliness == 12.8
    assert mountain.average_icy_days == 50.1
    assert mountain.average_rain == 10.01
    assert mountain.average_snow == 125.00
    assert len(mountain.trails) == 159
    assert len(mountain.lifts) == 20

    # difficulty = steepest_30m + weather_modifier (+ gladed/ungroomed bonus)
    assert mountain.trails["w11"].gladed is False
    assert mountain.trails["w11"].ungroomed is False
    assert mountain.trails["w11"].steepest_30m == 9.3
    assert mountain.trails["w11"].difficulty == 12.8
