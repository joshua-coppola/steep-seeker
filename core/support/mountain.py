from dataclasses import dataclass, fields, field
from typing import Self, Optional, Dict
from datetime import datetime
from shapely import Point

from core.datamodels.state import State
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.database import MountainTable
from core.support.trail import Trail
from core.support.lift import Lift
from core.osm.osm_processor import OSMProcessor
from core.connectors.database import cursor, DATABASE_PATH


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
    coordinates: Point
    season_passes: Optional[list[Season_Pass]] = field(default_factory=list)
    url: Optional[str] = None
    vertical: Optional[int] = None
    difficulty: Optional[float] = None
    beginner_friendliness: Optional[float] = None
    avg_icy_days: Optional[float] = None
    avg_snow: Optional[float] = None
    avg_rain: Optional[float] = None
    last_updated: Optional[datetime] = datetime.now()
    trails: Optional[Dict[str, Trail]] = field(default_factory=dict)
    lifts: Optional[Dict[str, Lift]] = field(default_factory=dict)

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

    def to_db(self, db_path: str = DATABASE_PATH) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        # check that all fields have been populated before saving
        missing_fields = [f.name for f in fields(self) if getattr(self, f.name) is None]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")

        with cursor(db_path=db_path) as cur:
            query = f"""
                INSERT INTO Mountains (
                    {MountainTable.mountain_id},
                    {MountainTable.name},
                    {MountainTable.state},
                    {MountainTable.direction},
                    {MountainTable.coordinates}
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mountain_id) DO UPDATE SET
                    name = excluded.name,
                    state = excluded.state,
                    direction = excluded.direction,
                    {MountainTable.coordinates} = excluded.{MountainTable.coordinates}
            """
            params = (
                self.id,
                self.name,
                self.state.value,
                self.direction,
                str(self.coordinates),
            )
            cur.execute(query, params)

    def from_osm(filename: str, season_passes: list[Season_Pass]) -> Self:
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
            coordinates=processor.get_center(),
            season_passes=season_passes,
        )

        return mountain
