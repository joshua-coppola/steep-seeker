import pytest
from shapely import LineString

from core.support.mountain import Mountain
from core.support.trail import Trail
from core.support.lift import Lift
from core.enum.state import State


@pytest.fixture
def mountain(trail, lift):
    mountain_dict = {
        "id": 1,
        "name": "Test",
        "state": State("VT"),
        "direction": "n",
        "season_passes": ["Epic", "Ikon"],
        "vertical": 1024,
        "difficulty": 89,
        "beginner_friendliness": 1,
        "trails": {"w1000": trail},
        "lifts": {"w1001": lift},
    }

    return Mountain(**mountain_dict)


@pytest.fixture
def trail():
    trail_dict = {
        "id": "w1000",
        "mountain_id": 1,
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
        "mountain_id": 1,
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
