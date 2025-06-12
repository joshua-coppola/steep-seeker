from core.support.mountain import Mountain, Trail, Lift
from core.support.states import State, Region

from shapely import LineString
from datetime import datetime
import pytest


@pytest.fixture
def mountain():
    mountain_dict = {
        "id": 1,
        "name": "Test",
        "state": State("VT"),
        "direction": "n",
        "season_passes": ["Epic", "Ikon"],
        "trail_count": 42,
        "lift_count": 0,
        "vertical": 1024,
        "difficulty": 89,
        "beginner_friendliness": 1,
    }

    return Mountain(**mountain_dict)


@pytest.fixture
def trail():
    trail_dict = {
        "id": "w1000",
        "geometry": LineString([[1, 1], [0, 0]]),
        "name": "Test",
        "official_rating": "Expert",
        "gladed": True,
        "area": False,
        "ungroomed": False,
        "park": False,
    }

    return Trail(**trail_dict)


@pytest.fixture
def lift():
    lift_dict = {
        "id": "w1001",
        "geometry": LineString([[1, 1], [0, 0]]),
        "name": "Test",
        "lift_type": "chair_lift",
        "occupancy": 4,
        "capacity": 1200,
        "detatchable": False,
        "bubble": False,
        "heating": False,
    }

    return Lift(**lift_dict)


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


def test_mountain_from_db():
    id = "w1000"

    mountain = Mountain.from_db(id)

    assert mountain == "TODO"


def test_mountain_to_db(mountain):
    assert mountain.to_db() == "TODO"


def test_trail(trail):
    assert trail.geometry == LineString([[1, 1], [0, 0]])


def test_trail_from_db():
    id = "w1000"

    trail = Trail.from_db(id)

    assert trail == "TODO"


def test_trail_to_db(trail):
    assert trail.to_db() == "TODO"


def test_lift(lift):
    assert lift.geometry == LineString([[1, 1], [0, 0]])


def test_lift_from_db():
    id = "w1000"

    lift = Lift.from_db(id)

    assert lift == "TODO"


def test_lift_to_db(lift):
    assert lift.to_db() == "TODO"
