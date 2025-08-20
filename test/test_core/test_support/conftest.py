import pytest
from shapely import LineString, Point
from datetime import datetime

from core.support.mountain import Mountain
from core.support.trail import Trail
from core.support.lift import Lift
from core.datamodels.state import State
from core.datamodels.season_pass import Season_Pass
from core.datamodels.database import MountainTable, TrailTable, LiftTable


@pytest.fixture
def mountain(trail, lift):
    mountain_dict = {
        MountainTable.mountain_id: 1,
        MountainTable.name: "Test",
        MountainTable.state: State.VERMONT,
        MountainTable.direction: "n",
        MountainTable.coordinates: Point(1, 1),
        MountainTable.season_passes: [Season_Pass.EPIC, Season_Pass.IKON],
        MountainTable.url: "https://test.com",
        MountainTable.vertical: 1024,
        MountainTable.difficulty: 89,
        MountainTable.beginner_friendliness: 1,
        MountainTable.average_icy_days: 25,
        MountainTable.average_snow: 150,
        MountainTable.average_rain: 10,
        MountainTable.trails: {trail.trail_id: trail},
        MountainTable.lifts: {lift.lift_id: lift},
        MountainTable.last_updated: datetime(2000, 2, 5, 12, 30, 5),
    }

    return Mountain(**mountain_dict)


@pytest.fixture
def trail():
    trail_dict = {
        TrailTable.trail_id: "w1000",
        TrailTable.mountain_id: 1,
        TrailTable.geometry: LineString([[1, 1], [0, 0]]),
        TrailTable.name: "Test",
        TrailTable.official_rating: "Expert",
        TrailTable.gladed: True,
        TrailTable.area: False,
        TrailTable.ungroomed: False,
        TrailTable.park: False,
        TrailTable.length: 1,
        TrailTable.vertical: 1,
        TrailTable.difficulty: 1.0,
        TrailTable.max_slope: 1.0,
        TrailTable.average_slope: 1.0,
    }

    return Trail(**trail_dict)


@pytest.fixture
def lift():
    lift_dict = {
        LiftTable.lift_id: "w1001",
        LiftTable.mountain_id: 1,
        LiftTable.geometry: LineString([[1, 1], [0, 0]]),
        LiftTable.name: "Test",
        LiftTable.lift_type: "chair_lift",
        LiftTable.occupancy: 4,
        LiftTable.capacity: 1200,
        LiftTable.detachable: False,
        LiftTable.bubble: False,
        LiftTable.heating: False,
        LiftTable.length: 1,
        LiftTable.vertical: 1,
        LiftTable.average_slope: 1.0,
    }

    return Lift(**lift_dict)
