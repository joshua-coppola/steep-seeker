import pytest
from shapely import LineString

from core.connectors.database import cursor
from core.datamodels.database import LiftTable
from core.support.lift import Lift


def test_lift(lift_factory):
    lift = lift_factory()
    assert lift.geometry == LineString([[1, 1, 10], [0, 0, 0]])


def test_lift_from_db(lift_factory, db_path):
    lift = lift_factory()
    with cursor(db_path=db_path) as cur:
        query = f"""
            INSERT INTO Lifts (
                {LiftTable.lift_id},
                {LiftTable.mountain_id},
                {LiftTable.geometry},
                {LiftTable.name},
                {LiftTable.lift_type},
                {LiftTable.occupancy},
                {LiftTable.capacity},
                {LiftTable.detachable},
                {LiftTable.bubble},
                {LiftTable.heating},
                {LiftTable.length},
                {LiftTable.vertical},
                {LiftTable.average_slope}
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            lift.lift_id,
            lift.mountain_id,
            str(lift.geometry),
            lift.name,
            lift.lift_type,
            lift.occupancy,
            lift.capacity,
            lift.detachable,
            lift.bubble,
            lift.heating,
            lift.length,
            lift.vertical,
            lift.average_slope,
        )
        cur.execute(query, params)
    returned_lift = Lift.from_db(lift.lift_id, db_path)

    assert lift == returned_lift

    assert Lift.from_db("fake_id", db_path) is None


def test_lift_to_db(lift_factory, db_path):
    lift = lift_factory()
    lift.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Lifts"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1

    expected_result = {
        LiftTable.lift_id: "w1001",
        LiftTable.mountain_id: "1",
        LiftTable.geometry: "LINESTRING Z (1 1 10, 0 0 0)",
        LiftTable.name: "Test",
        LiftTable.lift_type: "chair_lift",
        LiftTable.occupancy: 4,
        LiftTable.capacity: 1200,
        LiftTable.detachable: 0,
        LiftTable.bubble: 0,
        LiftTable.heating: 0,
        LiftTable.length: 1.0,
        LiftTable.vertical: 1.0,
        LiftTable.average_slope: 1.0,
    }

    assert dict(result[0]) == expected_result

    lift.capacity = 600
    expected_result[LiftTable.capacity] = 600

    lift.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Lifts"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1
    assert dict(result[0]) == expected_result

    lift.name = None

    with pytest.raises(Exception) as exc_info:
        lift.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)


def test_lift_to_db_allows_missing_osm_tag_fields(lift_factory, db_path):
    # occupancy/capacity/detachable/bubble/heating all come from OSM tags
    # that many real lifts aren't tagged with (matches the old schema's
    # nullability for these columns)
    lift = lift_factory(
        occupancy=None,
        capacity=None,
        detachable=None,
        bubble=None,
        heating=None,
    )

    lift.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = dict(cur.execute("SELECT * FROM Lifts").fetchall()[0])

    assert result[LiftTable.occupancy] is None
    assert result[LiftTable.capacity] is None
    assert result[LiftTable.detachable] is None
    assert result[LiftTable.bubble] is None
    assert result[LiftTable.heating] is None

    returned_lift = Lift.from_db(lift.lift_id, db_path)
    assert returned_lift.occupancy is None
    assert returned_lift.capacity is None
    assert returned_lift.detachable is None
    assert returned_lift.bubble is None
    assert returned_lift.heating is None
