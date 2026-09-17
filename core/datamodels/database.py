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
    hazardous: str = "hazardous"
    length: str = "length"
    vertical: str = "vertical"
    difficulty: str = "difficulty"
    max_slope: str = "max_slope"
    average_slope: str = "average_slope"
    steepest_100ft: str = "steepest_100ft"
    steepest_150ft: str = "steepest_150ft"
    steepest_300ft: str = "steepest_300ft"
    steepest_500ft: str = "steepest_500ft"
    steepest_1320ft: str = "steepest_1320ft"
    steepest_2640ft: str = "steepest_2640ft"
    steepest_5280ft: str = "steepest_5280ft"


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


@dataclass
class CachedWeatherTable:
    point: str = "point"
    season: str = "season"
    month: str = "month"
    icy_days: str = "icy_days"
    rain: str = "rain"
    snow: str = "snow"


@dataclass
class BlacklistTable:
    item_id: str = "item_id"
    mountain_id: str = "mountain_id"


@dataclass
class WeatherCalibrationTable:
    id: str = "id"
    created: str = "created"
    n_resorts: str = "n_resorts"
    icy_days: str = "icy_days"
    rain: str = "rain"
    snow: str = "snow"
