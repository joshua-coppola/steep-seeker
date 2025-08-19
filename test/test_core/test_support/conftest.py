import pytest
from shapely import LineString, Point
from datetime import datetime

from core.support.mountain import Mountain
from core.support.trail import Trail
from core.support.lift import Lift
from core.datamodels.state import State
from core.datamodels.season_pass import Season_Pass


@pytest.fixture
def mountain(trail, lift):
    mountain_dict = {
        "id": 1,
        "name": "Test",
        "state": State.VERMONT,
        "direction": "n",
        "coordinates": Point(1, 1),
        "season_passes": [Season_Pass.EPIC, Season_Pass.IKON],
        "url": "https://test.com",
        "vertical": 1024,
        "difficulty": 89,
        "beginner_friendliness": 1,
        "average_icy_days": 25,
        "average_snow": 150,
        "average_rain": 10,
        "trails": {"w1000": trail},
        "lifts": {"w1001": lift},
        "last_updated": datetime(2000, 2, 5, 12, 30, 5),
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
