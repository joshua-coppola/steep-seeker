from dataclasses import dataclass, fields
from typing import Self, Optional
from shapely import LineString, Polygon, wkt

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
    length: Optional[float]
    vertical: Optional[float] = None
    difficulty: Optional[float] = None
    max_slope: Optional[float] = None
    average_slope: Optional[float] = None
    steepest_30m: Optional[float] = None
    steepest_50m: Optional[float] = None
    steepest_100m: Optional[float] = None
    steepest_200m: Optional[float] = None
    steepest_500m: Optional[float] = None
    steepest_1000m: Optional[float] = None
    interior_geometry: Optional[LineString | Polygon] = ""
    route: Optional[LineString] = None

    def from_db(trail_id: str, db_path: str = DATABASE_PATH) -> Self:
        """
        Gets trail data from database and returns a Trail object
        """
        with cursor(db_path=db_path) as cur:
            query = "SELECT * from Trails WHERE trail_id = ?"
            params = (trail_id,)
            result = cur.execute(query, params).fetchone()

        if not result:
            return None

        result = dict(result)
        result[TrailTable.geometry] = wkt.loads(result[TrailTable.geometry])
        result[TrailTable.interior_geometry] = (
            wkt.loads(result[TrailTable.interior_geometry])
            if result[TrailTable.interior_geometry]
            else None
        )
        result[TrailTable.route] = (
            wkt.loads(result[TrailTable.route]) if result[TrailTable.route] else None
        )
        result[TrailTable.gladed] = bool(result[TrailTable.gladed])
        result[TrailTable.area] = bool(result[TrailTable.area])
        result[TrailTable.ungroomed] = bool(result[TrailTable.ungroomed])
        result[TrailTable.park] = bool(result[TrailTable.park])

        return Trail(**result)

    def to_db(self, db_path: str = DATABASE_PATH) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        # steepest_Xm fields may legitimately be None: a trail shorter than
        # the window has no segment of that length to measure
        nullable_fields = {
            "steepest_30m",
            "steepest_50m",
            "steepest_100m",
            "steepest_200m",
            "steepest_500m",
            "steepest_1000m",
            "route",
        }

        # check that all other fields have been populated before saving
        missing_fields = [
            f.name
            for f in fields(self)
            if f.name not in nullable_fields and getattr(self, f.name) is None
        ]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")

        if self.interior_geometry == "" and self.area:
            raise ValueError("The following fields are missing: interior_geometry")

        if self.route is None and self.area:
            raise ValueError("The following fields are missing: route")

        with cursor(db_path=db_path) as cur:
            query = f"""
                INSERT INTO Trails (
                    {TrailTable.trail_id},
                    {TrailTable.mountain_id},
                    {TrailTable.geometry},
                    {TrailTable.interior_geometry},
                    {TrailTable.route},
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
                    {TrailTable.average_slope},
                    {TrailTable.steepest_30m},
                    {TrailTable.steepest_50m},
                    {TrailTable.steepest_100m},
                    {TrailTable.steepest_200m},
                    {TrailTable.steepest_500m},
                    {TrailTable.steepest_1000m}
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({TrailTable.trail_id}) DO UPDATE SET
                    {TrailTable.mountain_id} = excluded.{TrailTable.mountain_id},
                    {TrailTable.geometry} = excluded.{TrailTable.geometry},
                    {TrailTable.interior_geometry} = excluded.{TrailTable.interior_geometry},
                    {TrailTable.route} = excluded.{TrailTable.route},
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
                    {TrailTable.average_slope} = excluded.{TrailTable.average_slope},
                    {TrailTable.steepest_30m} = excluded.{TrailTable.steepest_30m},
                    {TrailTable.steepest_50m} = excluded.{TrailTable.steepest_50m},
                    {TrailTable.steepest_100m} = excluded.{TrailTable.steepest_100m},
                    {TrailTable.steepest_200m} = excluded.{TrailTable.steepest_200m},
                    {TrailTable.steepest_500m} = excluded.{TrailTable.steepest_500m},
                    {TrailTable.steepest_1000m} = excluded.{TrailTable.steepest_1000m}
            """
            params = (
                self.trail_id,
                self.mountain_id,
                str(self.geometry),
                str(self.interior_geometry),
                str(self.route) if self.route is not None else None,
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
                self.steepest_30m,
                self.steepest_50m,
                self.steepest_100m,
                self.steepest_200m,
                self.steepest_500m,
                self.steepest_1000m,
            )
            cur.execute(query, params)
