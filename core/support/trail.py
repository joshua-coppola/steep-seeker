from dataclasses import dataclass, fields
from typing import Self, Optional
from shapely import LineString, Polygon

from core.connectors.database import cursor, DATABASE_PATH
from core.datamodels.database import TrailTable


@dataclass
class Trail:
    """
    Trail dataclass that contains all information about a specific trail.
    An existing trail can be loaded from the DB with from_db, and a new
    or updated trail can be saved back to the DB with to_db.
    """

    trail_id: str
    mountain_id: int
    geometry: LineString | Polygon
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
                INSERT INTO Trails (
                    {TrailTable.trail_id},
                    {TrailTable.mountain_id},
                    {TrailTable.geometry},
                    {TrailTable.name},
                    {TrailTable.official_rating},
                    {TrailTable.gladed},
                    {TrailTable.area},
                    {TrailTable.ungroomed},
                    {TrailTable.park},
                    {TrailTable.length},
                    {TrailTable.vertical},
                    {TrailTable.difficulty},
                    {TrailTable.max_slope},
                    {TrailTable.average_slope}
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({TrailTable.trail_id}) DO UPDATE SET
                    {TrailTable.mountain_id} = excluded.{TrailTable.mountain_id},
                    {TrailTable.geometry} = excluded.{TrailTable.geometry},
                    {TrailTable.name} = excluded.{TrailTable.name},
                    {TrailTable.official_rating} = excluded.{TrailTable.official_rating},
                    {TrailTable.gladed} = excluded.{TrailTable.gladed},
                    {TrailTable.area} = excluded.{TrailTable.area},
                    {TrailTable.ungroomed} = excluded.{TrailTable.ungroomed},
                    {TrailTable.park} = excluded.{TrailTable.park},
                    {TrailTable.length} = excluded.{TrailTable.length},
                    {TrailTable.vertical} = excluded.{TrailTable.vertical},
                    {TrailTable.difficulty} = excluded.{TrailTable.difficulty},
                    {TrailTable.max_slope} = excluded.{TrailTable.max_slope},
                    {TrailTable.average_slope} = excluded.{TrailTable.average_slope}
            """
            params = (
                self.trail_id,
                self.mountain_id,
                str(self.geometry),
                self.name,
                self.official_rating,
                self.gladed,
                self.area,
                self.ungroomed,
                self.park,
                self.length,
                self.vertical,
                self.difficulty,
                self.max_slope,
                self.average_slope,
            )
            cur.execute(query, params)
