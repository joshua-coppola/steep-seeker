from core.support.mountain import Trail, Lift
from shapely import LineString


def test_trail():
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

    trail = Trail(**trail_dict)

    assert trail.geometry == trail_dict["geometry"]


def test_trail_from_db():
    id = "w1000"

    trail = Trail.from_db(id)

    assert trail == "TODO"


def test_trail_to_db():
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

    trail = Trail(**trail_dict)

    assert trail.to_db() == "TODO"


def test_lift():
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

    lift = Lift(**lift_dict)

    assert lift.geometry == lift_dict["geometry"]


def test_lift_from_db():
    id = "w1000"

    lift = Lift.from_db(id)

    assert lift == "TODO"


def test_lift_to_db():
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

    lift = Lift(**lift_dict)

    assert lift.to_db() == "TODO"
