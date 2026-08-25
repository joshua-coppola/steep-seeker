import pytest

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.trail_query import list_trails


@pytest.fixture
def seeded_db_path(mountain_factory, trail_factory, db_path):
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={
            "1-a": trail_factory(
                trail_id="1-a",
                mountain_id="1",
                name="Trail A",
                difficulty=80,
                length=500,
                max_slope=45,
                average_slope=30,
            ),
            "1-b": trail_factory(
                trail_id="1-b",
                mountain_id="1",
                name="Trail B",
                difficulty=20,
                length=100,
                max_slope=15,
                average_slope=10,
            ),
            "1-unnamed": trail_factory(
                trail_id="1-unnamed",
                mountain_id="1",
                name="",
                difficulty=99,
                length=50,
            ),
        },
        lifts={},
    ).to_db(db_path)
    mountain_factory(
        mountain_id="2",
        name="Alta",
        state=State.UTAH,
        trails={
            "2-c": trail_factory(
                trail_id="2-c",
                mountain_id="2",
                name="Trail C",
                difficulty=95,
                length=1000,
                max_slope=50,
                average_slope=35,
            ),
        },
        lifts={},
    ).to_db(db_path)

    return db_path


def test_list_trails_returns_all_named_trails_by_default(seeded_db_path):
    summaries, total_count = list_trails(db_path=seeded_db_path)

    assert total_count == 3
    assert {s.name for s in summaries} == {"Trail A", "Trail B", "Trail C"}


def test_list_trails_excludes_unnamed_trails(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path)

    assert "" not in {s.name for s in summaries}


def test_list_trails_filters_by_region(seeded_db_path):
    summaries, total_count = list_trails(db_path=seeded_db_path, region=Region.WEST)

    assert total_count == 1
    assert summaries[0].name == "Trail C"


def test_list_trails_filters_by_state(seeded_db_path):
    summaries, total_count = list_trails(db_path=seeded_db_path, state=State.VERMONT)

    assert total_count == 2
    assert {s.name for s in summaries} == {"Trail A", "Trail B"}


def test_list_trails_sorts_by_difficulty_desc(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path, sort="difficulty")

    assert [s.name for s in summaries] == ["Trail C", "Trail A", "Trail B"]


def test_list_trails_sorts_by_length_desc(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path, sort="length")

    assert [s.name for s in summaries] == ["Trail C", "Trail A", "Trail B"]


def test_list_trails_paginates(seeded_db_path):
    summaries, total_count = list_trails(
        db_path=seeded_db_path, sort="difficulty", limit=1, offset=1
    )

    assert total_count == 3
    assert [s.name for s in summaries] == ["Trail A"]


def test_list_trails_includes_resort_name_and_state(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path, state=State.UTAH)

    assert summaries[0].resort_name == "Alta"
    assert summaries[0].state == State.UTAH


def test_list_trails_length_converted_to_feet(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path, state=State.UTAH)

    assert summaries[0].length == round(1000 * 3.28084)


def test_list_trails_includes_max_and_average_slope(seeded_db_path):
    summaries, _ = list_trails(db_path=seeded_db_path, state=State.UTAH)

    assert summaries[0].max_slope == 50
    assert summaries[0].average_slope == 35
