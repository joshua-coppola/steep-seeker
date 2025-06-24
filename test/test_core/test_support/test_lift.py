from shapely import LineString
import pytest

from core.support.lift import Lift


def test_lift(lift):
    assert lift.geometry == LineString([[1, 1], [0, 0]])


def test_lift_from_db():
    id = "w1000"

    lift = Lift.from_db(id)

    assert lift == "TODO"


def test_lift_to_db(lift):
    with pytest.raises(Exception) as exc_info:
        lift.to_db()

    assert "fields are missing" in str(exc_info)

    lift.length = 1
    lift.vertical = 1
    lift.average_slope = 1

    assert lift.to_db() == "TODO"
