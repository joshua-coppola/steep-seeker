from dataclasses import dataclass, fields
from typing import Self, Optional
from shapely import LineString

from core.connectors.database import DATABASE_PATH


@dataclass
class Lift:
    """
    Lift dataclass that contains all information about a specific lift.
    An existing lift can be loaded from the DB with from_db, and a new
    or updated lift can be saved back to the DB with to_db.
    """

    lift_id: str
    mountain_id: int
    geometry: LineString
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

    def from_db(lift_id: str, db_path: str = DATABASE_PATH) -> Self:
        """
        Gets lift data from database and returns a Lift object
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
        return "TODO"
