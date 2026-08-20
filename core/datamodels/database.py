from dataclasses import dataclass


@dataclass
class MountainTable:
    mountain_id: str = "mountain_id"
    name: str = "name"
    state: str = "state"
    direction: str = "direction"
    coordinates: str = "coordinates"
    season_passes: str = "season_passes"
    vertical: str = "vertical"
    difficulty: str = "difficulty"
    beginner_friendliness: str = "beginner_friendliness"
    average_icy_days: str = "average_icy_days"
    average_snow: str = "average_snow"
    average_rain: str = "average_rain"
    last_updated: str = "last_updated"
    url: str = "url"
    # Not in SQL, only the python class
    trails: str = "trails"
    lifts: str = "lifts"


@dataclass
class TrailTable:
    trail_id: str = "trail_id"
    mountain_id: str = "mountain_id"
    geometry: str = "geometry"
    interior_geometry: str = "interior_geometry"
    route: str = "route"
    name: str = "name"
    official_rating: str = "official_rating"
    gladed: str = "gladed"
    area: str = "area"
    ungroomed: str = "ungroomed"
    park: str = "park"
    length: str = "length"
    vertical: str = "vertical"
    difficulty: str = "difficulty"
    max_slope: str = "max_slope"
    average_slope: str = "average_slope"
    steepest_30m: str = "steepest_30m"
    steepest_50m: str = "steepest_50m"
    steepest_100m: str = "steepest_100m"
    steepest_200m: str = "steepest_200m"
    steepest_500m: str = "steepest_500m"
    steepest_1000m: str = "steepest_1000m"


@dataclass
class LiftTable:
    lift_id: str = "lift_id"
    mountain_id: str = "mountain_id"
    geometry: str = "geometry"
    name: str = "name"
    lift_type: str = "lift_type"
    occupancy: str = "occupancy"
    capacity: str = "capacity"
    detachable: str = "detachable"
    bubble: str = "bubble"
    heating: str = "heating"
    length: str = "length"
    vertical: str = "vertical"
    average_slope: str = "average_slope"


@dataclass
class CacheTable:
    point: str = "point"
    elevation: str = "elevation"
