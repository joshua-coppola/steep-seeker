import pytest
from shapely import Point

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.mountain_query import list_mountains


def _trails(trail_factory, mountain_id, count):
    return {
        f"{mountain_id}-t{i}": trail_factory(
            trail_id=f"{mountain_id}-t{i}", mountain_id=mountain_id
        )
        for i in range(count)
    }


@pytest.fixture
def seeded_db_path(mountain_factory, trail_factory, db_path):
    # lifts=() forces each mountain to get its own zero-lift default rather
    # than sharing the factory's fixed default lift_id across mountains
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        difficulty=40,
        trails=_trails(trail_factory, "1", 3),
        lifts={},
    ).to_db(db_path)
    mountain_factory(
        mountain_id="2",
        name="Killington",
        state=State.VERMONT,
        difficulty=70,
        trails=_trails(trail_factory, "2", 10),
        lifts={},
    ).to_db(db_path)
    mountain_factory(
        mountain_id="3",
        name="Alta",
        state=State.UTAH,
        difficulty=90,
        trails=_trails(trail_factory, "3", 5),
        lifts={},
    ).to_db(db_path)

    return db_path


def test_list_mountains_returns_all_by_default(seeded_db_path):
    summaries, total_count = list_mountains(db_path=seeded_db_path)

    assert total_count == 3
    assert {s.name for s in summaries} == {"Bolton Valley", "Killington", "Alta"}


def test_list_mountains_filters_by_region(seeded_db_path):
    summaries, total_count = list_mountains(
        db_path=seeded_db_path, region=Region.NORTHEAST
    )

    assert total_count == 2
    assert {s.name for s in summaries} == {"Bolton Valley", "Killington"}


def test_list_mountains_filters_by_state(seeded_db_path):
    summaries, total_count = list_mountains(db_path=seeded_db_path, state=State.UTAH)

    assert total_count == 1
    assert summaries[0].name == "Alta"


def test_list_mountains_filters_by_difficulty_range(seeded_db_path):
    summaries, _ = list_mountains(
        db_path=seeded_db_path, difficulty_min=60, difficulty_max=100
    )

    assert {s.name for s in summaries} == {"Killington", "Alta"}


def test_list_mountains_filters_by_trail_count_range(seeded_db_path):
    summaries, _ = list_mountains(
        db_path=seeded_db_path, trail_count_min=0, trail_count_max=4
    )

    assert {s.name for s in summaries} == {"Bolton Valley"}


def test_list_mountains_sorts_by_trail_count_desc(seeded_db_path):
    summaries, _ = list_mountains(
        db_path=seeded_db_path, sort="trail_count", order="desc"
    )

    assert [s.name for s in summaries] == ["Killington", "Alta", "Bolton Valley"]


def test_list_mountains_paginates(seeded_db_path):
    summaries, total_count = list_mountains(
        db_path=seeded_db_path, sort="name", order="asc", limit=1, offset=1
    )

    assert total_count == 3
    assert [s.name for s in summaries] == ["Bolton Valley"]


def test_mountain_summary_region_computed(seeded_db_path):
    summaries, _ = list_mountains(db_path=seeded_db_path, state=State.VERMONT)

    assert all(s.region() == Region.NORTHEAST for s in summaries)


def test_list_mountains_handles_empty_season_passes(mountain_factory, db_path):
    # to_db stores an empty season_passes list as "" (",".join([]) == "");
    # list_mountains must not try to build a Season_Pass("") out of that
    mountain_factory(mountain_id="4", name="No Pass Mountain", season_passes=[]).to_db(
        db_path
    )

    summaries, _ = list_mountains(db_path=db_path)

    assert summaries[0].season_passes == []


def test_mountain_summary_vertical_converted_to_feet(mountain_factory, db_path):
    # Mountain.vertical is stored in meters; MountainSummary is a display
    # DTO, so its vertical should already be feet by the time a template
    # sees it
    mountain_factory(mountain_id="5", name="Meters Mountain", vertical=1024).to_db(
        db_path
    )

    summaries, _ = list_mountains(db_path=db_path)

    assert summaries[0].vertical == round(1024 * 3.28084)


def test_mountain_summary_includes_coordinates(mountain_factory, db_path):
    mountain_factory(
        mountain_id="6", name="Coordinates Mountain", coordinates=Point(-72.5, 43.5)
    ).to_db(db_path)

    summaries, _ = list_mountains(db_path=db_path)

    assert summaries[0].coordinates == Point(-72.5, 43.5)
