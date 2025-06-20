from shapely import LineString
import pytest

from core.support.trail import Trail


def test_trail(trail):
    assert trail.geometry == LineString([[1, 1], [0, 0]])


def test_trail_from_db():
    id = "w1000"

    trail = Trail.from_db(id)

    assert trail == "TODO"


def test_trail_to_db(trail):
    with pytest.raises(Exception) as exc_info:
        trail.to_db()

    assert "fields are missing" in str(exc_info)

    trail.length = 1
    trail.vertical = 1
    trail.difficulty = 1
    trail.max_slope = 1
    trail.average_slope = 1

    assert trail.to_db() == "TODO"
