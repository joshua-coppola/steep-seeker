from core.support.mountain import Mountain
from core.support.states import Region

from datetime import datetime
import pytest


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


def test_mountain_to_db(mountain):
    assert mountain.to_db() == "TODO"

    mountain.name = None

    with pytest.raises(Exception) as exc_info:
        mountain.to_db()

    assert "fields are missing" in str(exc_info)
