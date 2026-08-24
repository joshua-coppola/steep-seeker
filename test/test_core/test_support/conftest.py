from datetime import datetime, timezone

import pytest
from shapely import LineString, Point

from core.datamodels.database import LiftTable, MountainTable, TrailTable
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.lift import Lift
from core.support.mountain import Mountain
from core.support.trail import Trail


@pytest.fixture
def trail_factory():
    def _make_trail(**overrides):
        trail_dict = {
            TrailTable.trail_id: "w1000",
            TrailTable.mountain_id: 1,
            TrailTable.geometry: LineString(
                [[1, 1, 10], [0, 0, 0]]
            ),  # lon, lat, elevation
            TrailTable.interior_geometry: LineString([[1, 1, 10], [0, 0, 0]]),
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
            TrailTable.steepest_30m: 1.0,
            TrailTable.steepest_50m: 1.0,
            TrailTable.steepest_100m: 1.0,
            TrailTable.steepest_200m: 1.0,
            TrailTable.steepest_500m: 1.0,
            TrailTable.steepest_1000m: 1.0,
        }
        trail_dict.update(overrides)
        return Trail(**trail_dict)

    return _make_trail


@pytest.fixture
def lift_factory():
    def _make_lift(**overrides):
        lift_dict = {
            LiftTable.lift_id: "w1001",
            LiftTable.mountain_id: 1,
            LiftTable.geometry: LineString([[1, 1, 10], [0, 0, 0]]),
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
        lift_dict.update(overrides)
        return Lift(**lift_dict)

    return _make_lift


@pytest.fixture
def mountain_factory(trail_factory, lift_factory):
    def _make_mountain(**overrides):
        mountain_id = overrides.get(MountainTable.mountain_id, 1)
        trails = overrides.pop("trails", None)
        lifts = overrides.pop("lifts", None)

        if trails is None:
            default_trail = trail_factory(**{TrailTable.mountain_id: mountain_id})
            trails = {default_trail.trail_id: default_trail}
        if lifts is None:
            default_lift = lift_factory(**{LiftTable.mountain_id: mountain_id})
            lifts = {default_lift.lift_id: default_lift}

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
            MountainTable.trails: trails,
            MountainTable.lifts: lifts,
            MountainTable.last_updated: datetime(
                2000, 2, 5, 12, 30, 5, tzinfo=timezone.utc
            ),
        }
        mountain_dict.update(overrides)
        return Mountain(**mountain_dict)

    return _make_mountain
