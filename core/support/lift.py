from dataclasses import dataclass, fields
from typing import Self, Optional
from shapely import LineString, wkt

from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import LiftTable


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
    detachable: bool
    bubble: bool
    heating: bool
    length: Optional[float] = None
    vertical: Optional[float] = None
    average_slope: Optional[float] = None

    def from_db(lift_id: str, db_path: str = DATABASE_PATH) -> Self:
        """
        Gets lift data from database and returns a Lift object
        """
        with cursor(db_path=db_path) as cur:
            query = "SELECT * from Lifts WHERE lift_id = ?"
            params = (lift_id,)
            result = cur.execute(query, params).fetchone()

        if not result:
            return None

        result = dict(result)
        result[LiftTable.geometry] = wkt.loads(result[LiftTable.geometry])

        return Lift(**result)

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
                INSERT INTO Lifts (
                    {LiftTable.lift_id},
                    {LiftTable.mountain_id},
                    {LiftTable.geometry},
                    {LiftTable.name},
                    {LiftTable.lift_type},
                    {LiftTable.occupancy},
                    {LiftTable.capacity},
                    {LiftTable.detachable},
                    {LiftTable.bubble},
                    {LiftTable.heating},
                    {LiftTable.length},
                    {LiftTable.vertical},
                    {LiftTable.average_slope}
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({LiftTable.lift_id}) DO UPDATE SET
                    {LiftTable.mountain_id} = excluded.{LiftTable.mountain_id},
                    {LiftTable.geometry} = excluded.{LiftTable.geometry},
                    {LiftTable.name} = excluded.{LiftTable.name},
                    {LiftTable.lift_type} = excluded.{LiftTable.lift_type},
                    {LiftTable.occupancy} = excluded.{LiftTable.occupancy},
                    {LiftTable.capacity} = excluded.{LiftTable.capacity},
                    {LiftTable.detachable} = excluded.{LiftTable.detachable},
                    {LiftTable.bubble} = excluded.{LiftTable.bubble},
                    {LiftTable.heating} = excluded.{LiftTable.heating},
                    {LiftTable.length} = excluded.{LiftTable.length},
                    {LiftTable.vertical} = excluded.{LiftTable.vertical},
                    {LiftTable.average_slope} = excluded.{LiftTable.average_slope}
            """
            params = (
                self.lift_id,
                self.mountain_id,
                str(self.geometry),
                self.name,
                self.lift_type,
                self.occupancy,
                self.capacity,
                self.detachable,
                self.bubble,
                self.heating,
                self.length,
                self.vertical,
                self.average_slope,
            )
            cur.execute(query, params)
