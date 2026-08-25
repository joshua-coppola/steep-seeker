import pytest

from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.lift_query import list_lifts


@pytest.fixture
def seeded_db_path(mountain_factory, lift_factory, db_path):
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={},
        lifts={
            "1-a": lift_factory(
                lift_id="1-a",
                mountain_id="1",
                name="Lift A",
                vertical=500,
                length=2000,
                average_slope=25,
                occupancy=4,
                capacity=1200,
                detachable=True,
                bubble=False,
                heating=False,
            ),
            "1-b": lift_factory(
                lift_id="1-b",
                mountain_id="1",
                name="Lift B",
                vertical=100,
                length=400,
                average_slope=10,
                occupancy=2,
                capacity=None,
                detachable=False,
                bubble=True,
                heating=True,
            ),
            "1-unnamed": lift_factory(
                lift_id="1-unnamed",
                mountain_id="1",
                name="",
                vertical=900,
                length=3000,
            ),
        },
    ).to_db(db_path)
    mountain_factory(
        mountain_id="2",
        name="Alta",
        state=State.UTAH,
        trails={},
        lifts={
            "2-c": lift_factory(
                lift_id="2-c",
                mountain_id="2",
                name="Lift C",
                vertical=800,
                length=2500,
                average_slope=20,
                occupancy=6,
                capacity=1800,
                detachable=True,
                bubble=True,
                heating=False,
            ),
        },
    ).to_db(db_path)

    return db_path


def test_list_lifts_returns_all_named_lifts_by_default(seeded_db_path):
    summaries, total_count = list_lifts(db_path=seeded_db_path)

    assert total_count == 3
    assert {s.name for s in summaries} == {"Lift A", "Lift B", "Lift C"}


def test_list_lifts_excludes_unnamed_lifts(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path)

    assert "" not in {s.name for s in summaries}


def test_list_lifts_filters_by_region(seeded_db_path):
    summaries, total_count = list_lifts(db_path=seeded_db_path, region=Region.WEST)

    assert total_count == 1
    assert summaries[0].name == "Lift C"


def test_list_lifts_filters_by_state(seeded_db_path):
    summaries, total_count = list_lifts(db_path=seeded_db_path, state=State.VERMONT)

    assert total_count == 2
    assert {s.name for s in summaries} == {"Lift A", "Lift B"}


def test_list_lifts_sorts_by_vertical_desc(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path, sort="vertical")

    assert [s.name for s in summaries] == ["Lift C", "Lift A", "Lift B"]


def test_list_lifts_sorts_by_average_slope_desc(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path, sort="average_slope")

    assert [s.name for s in summaries] == ["Lift A", "Lift C", "Lift B"]


def test_list_lifts_paginates(seeded_db_path):
    summaries, total_count = list_lifts(
        db_path=seeded_db_path, sort="vertical", limit=1, offset=1
    )

    assert total_count == 3
    assert [s.name for s in summaries] == ["Lift A"]


def test_list_lifts_includes_resort_name_and_state(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path, state=State.UTAH)

    assert summaries[0].resort_name == "Alta"
    assert summaries[0].state == State.UTAH


def test_list_lifts_vertical_and_length_converted_to_feet(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path, state=State.UTAH)

    assert summaries[0].vertical == round(800 * 3.28084)
    assert summaries[0].length == round(2500 * 3.28084)


def test_list_lifts_handles_none_capacity(seeded_db_path):
    summaries, _ = list_lifts(db_path=seeded_db_path, sort="vertical")

    lift_b = next(s for s in summaries if s.name == "Lift B")
    assert lift_b.capacity is None
