from dataclasses import dataclass, fields, field
from typing import Self, Optional
from datetime import datetime

from core.support.states import State, Region
from core.support.trail import Trail
from core.support.lift import Lift
from core.osm.osm_processor import OSMProcessor


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
    vertical: Optional[int] = None
    difficulty: Optional[float] = None
    beginner_friendliness: Optional[float] = None
    last_updated: Optional[datetime] = datetime.now()
    trails: Optional[dict] = field(default_factory=dict)
    lifts: Optional[dict] = field(default_factory=dict)

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

    def trail_count(self) -> int:
        """
        Returns the number of trails associated with the Mountain
        """
        return len(self.trails)

    def lift_count(self) -> int:
        """
        Returns the number of lifts associated with the Mountain
        """
        return len(self.lifts)

    def add_trail(self, trail: Trail) -> None:
        """
        Inserts a new trail into trails dict
        """
        self.trails[trail.id] = Trail

    def add_lift(self, lift: Lift) -> None:
        """
        Inserts a new trail into lifts dict
        """
        self.lifts[lift.id] = Lift

    def from_db(id: str) -> Self:
        """
        Gets mountain data from database and returns a Mountain object
        """
        return "TODO"

    def to_db(self) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        # check that all fields have been populated before saving
        missing_fields = [f.name for f in fields(self) if getattr(self, f.name) is None]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")
        return "TODO"

    def from_osm(filename: str, season_passes: list[str]) -> Self:
        """
        Gets mountain data from the provided OSM file and returns a
        Mountain object
        """
        processor = OSMProcessor(filename)

        mountain = Mountain(
            id=processor.mountain_id,
            name=filename.split("/")[-1].split(".osm")[0],
            state=processor.get_state(),
            direction=processor.get_direction(),
            season_passes=season_passes,
        )

        return mountain
