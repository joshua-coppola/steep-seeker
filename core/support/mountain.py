from dataclasses import dataclass
from shapely import LineString, Polygon
from typing import Self


@dataclass
class Trail:
    """
    Trail dataclass that contains all information about a specific trail.
    An existing trail can be loaded from the DB with from_db, and a new
    or updated trail can be saved back to the DB with to_db.
    """

    id: str
    geometry: LineString | Polygon
    name: str
    official_rating: str
    gladed: bool
    area: bool
    ungroomed: bool
    park: bool

    def from_db(id: str) -> Self:
        return "TODO"

    def to_db(self) -> None:
        return "TODO"


@dataclass
class Lift:
    """
    Lift dataclass that contains all information about a specific lift.
    An existing lift can be loaded from the DB with from_db, and a new
    or updated lift can be saved back to the DB with to_db.
    """

    id: str
    geometry: LineString
    name: str
    lift_type: str
    occupancy: int
    capacity: int
    detatchable: bool
    bubble: bool
    heating: bool

    def from_db(id: str) -> Self:
        return "TODO"

    def to_db(self) -> None:
        return "TODO"
