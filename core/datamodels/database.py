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


@dataclass
class TrailTable:
    trail_id: str = "trail_id"
    mountain_id: str = "mountain_id"
    geometry: str = "geometry"
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
    heated: str = "heated"
    length: str = "length"
    vertical: str = "vertical"
    average_slope: str = "average_slope"


@dataclass
class CacheTable:
    point: str = "point"
    elevation: str = "elevation"
