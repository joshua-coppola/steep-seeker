from dataclasses import dataclass
from typing import Self, Optional
from datetime import datetime

from core.support.states import State, Region


@dataclass
class Mountain:
    """
    Mountain dataclass that contains all information about a specific
    mountain. An existing mountain can be loaded from the DB with from_db,
    and a new or updated mountain can be saved back to the DB with to_db.
    """

    id: int
    name: str
    state: State
    direction: str
    season_passes: list
    trail_count: int
    lift_count: int
    vertical: int
    difficulty: float
    beginner_friendliness: float
    last_updated: Optional[datetime] = datetime.now()

    def region(self) -> Region:
        """
        Returns the geographic region the mountain is a part of
        (NORTHEAST, SOUTHEAST, MIDWEST, WEST)
        """
        return Region.get_region(self.state)

    def bearing(self) -> int:
        """
        Returns what the bearing should be for the top of the map.
        """
        if self.direction == "n":
            return 180
        if self.direction == "e":
            return 270
        if self.direction == "s":
            return 0
        if self.direction == "w":
            return 90
        raise ValueError(f"Invalid direction value: {self.direction}")

    def from_db(id: str) -> Self:
        """
        Gets mountain data from database and returns a Mountain object
        """
        return "TODO"

    def to_db(self) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        return "TODO"


@dataclass
class Trail:
    """
    Trail dataclass that contains all information about a specific trail.
    An existing trail can be loaded from the DB with from_db, and a new
    or updated trail can be saved back to the DB with to_db.
    """

    id: str
    mountain_id: int
    geometry: str
    name: str
    official_rating: str
    gladed: bool
    area: bool
    ungroomed: bool
    park: bool
    length: Optional[float] = None
    vertical: Optional[float] = None
    difficulty: Optional[float] = None
    max_slope: Optional[float] = None
    average_slope: Optional[float] = None

    def from_db(id: str) -> Self:
        """
        Gets trail data from database and returns a Trail object
        """
        return "TODO"

    def to_db(self) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        return "TODO"


@dataclass
class Lift:
    """
    Lift dataclass that contains all information about a specific lift.
    An existing lift can be loaded from the DB with from_db, and a new
    or updated lift can be saved back to the DB with to_db.
    """

    id: str
    mountain_id: int
    geometry: str
    name: str
    lift_type: str
    occupancy: int
    capacity: int
    detatchable: bool
    bubble: bool
    heating: bool
    length: Optional[float] = None
    vertical: Optional[float] = None
    average_slope: Optional[float] = None

    def from_db(id: str) -> Self:
        """
        Gets lift data from database and returns a Lift object
        """
        return "TODO"

    def to_db(self) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        return "TODO"
