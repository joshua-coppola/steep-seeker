from dataclasses import dataclass, fields
from typing import Self, Optional


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
        # check that all fields have been populated before saving
        missing_fields = [f.name for f in fields(self) if getattr(self, f.name) is None]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")
        """
        Updates DB record with the values in the dataclass
        """
        return "TODO"
