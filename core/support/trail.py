from dataclasses import dataclass, fields
from typing import Self

from shapely import LineString, MultiLineString, Polygon, wkt

from core.connectors.database import DATABASE_PATH, cursor, db_id
from core.datamodels.database import TrailTable
from core.support.utils import (
    difficulty_pitch_field,
    meters_to_feet,
    round_feet,
    round_geometry_precision,
)


@dataclass
class Trail:
    """
    Trail dataclass that contains all information about a specific trail.
    An existing trail can be loaded from the DB with from_db, and a new
    or updated trail can be saved back to the DB with to_db.
    """

    trail_id: str
    mountain_id: str
    geometry: LineString | Polygon | MultiLineString
    name: str
    official_rating: str | None
    gladed: bool
    area: bool
    multi_route: bool
    ungroomed: bool
    park: bool
    hazardous: bool
    length: float | None
    vertical: float | None = None
    difficulty: float | None = None
    max_slope: float | None = None
    average_slope: float | None = None
    steepest_100ft: float | None = None
    steepest_150ft: float | None = None
    steepest_300ft: float | None = None
    steepest_500ft: float | None = None
    steepest_1320ft: float | None = None
    steepest_2640ft: float | None = None
    steepest_5280ft: float | None = None
    interior_geometry: LineString | Polygon | None = ""
    route: LineString | None = None

    def length_feet(self) -> int | None:
        """
        Returns length in feet, for display. Length is stored in meters.
        """
        return round_feet(meters_to_feet(self.length))

    def vertical_feet(self) -> int | None:
        """
        Returns vertical drop in feet, for display. Vertical is stored
        in meters.
        """
        return round_feet(meters_to_feet(self.vertical))

    def difficulty_pitch(self) -> float | None:
        """
        The steepest_Xft value that fed this trail's difficulty rating (see
        difficulty_pitch_field) -- the pitch to show alongside a
        trail_color(self.difficulty) badge so the two stay consistent.
        """
        return getattr(self, difficulty_pitch_field())

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
        result[TrailTable.multi_route] = bool(result[TrailTable.multi_route])
        result[TrailTable.ungroomed] = bool(result[TrailTable.ungroomed])
        result[TrailTable.park] = bool(result[TrailTable.park])
        result[TrailTable.hazardous] = bool(result[TrailTable.hazardous])

        return Trail(**result)

    def to_db(self, db_path: str = DATABASE_PATH) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        # steepest_Xft fields may legitimately be None: a trail shorter than
        # the window has no segment of that length to measure. route and
        # interior_geometry are only meaningful for area trails (OSMProcessor
        # leaves them None for line trails); required-when-area is enforced
        # separately below. official_rating comes from OSM's
        # piste:difficulty tag, which many trails simply aren't tagged with
        nullable_fields = {
            "steepest_100ft",
            "steepest_150ft",
            "steepest_300ft",
            "steepest_500ft",
            "steepest_1320ft",
            "steepest_2640ft",
            "steepest_5280ft",
            "route",
            "interior_geometry",
            "official_rating",
        }

        # check that all other fields have been populated before saving
        missing_fields = [
            f.name
            for f in fields(self)
            if f.name not in nullable_fields and getattr(self, f.name) is None
        ]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")

        if self.interior_geometry in ("", None) and self.area:
            raise ValueError("The following fields are missing: interior_geometry")

        if self.route is None and (self.area or self.multi_route):
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
                    {TrailTable.multi_route},
                    {TrailTable.ungroomed},
                    {TrailTable.park},
                    {TrailTable.hazardous},
                    {TrailTable.length},
                    {TrailTable.vertical},
                    {TrailTable.difficulty},
                    {TrailTable.max_slope},
                    {TrailTable.average_slope},
                    {TrailTable.steepest_100ft},
                    {TrailTable.steepest_150ft},
                    {TrailTable.steepest_300ft},
                    {TrailTable.steepest_500ft},
                    {TrailTable.steepest_1320ft},
                    {TrailTable.steepest_2640ft},
                    {TrailTable.steepest_5280ft}
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({TrailTable.trail_id}) DO UPDATE SET
                    {TrailTable.mountain_id} = excluded.{TrailTable.mountain_id},
                    {TrailTable.geometry} = excluded.{TrailTable.geometry},
                    {TrailTable.interior_geometry} = excluded.{TrailTable.interior_geometry},
                    {TrailTable.route} = excluded.{TrailTable.route},
                    {TrailTable.name} = excluded.{TrailTable.name},
                    {TrailTable.official_rating} = excluded.{TrailTable.official_rating},
                    {TrailTable.gladed} = excluded.{TrailTable.gladed},
                    {TrailTable.area} = excluded.{TrailTable.area},
                    {TrailTable.multi_route} = excluded.{TrailTable.multi_route},
                    {TrailTable.ungroomed} = excluded.{TrailTable.ungroomed},
                    {TrailTable.park} = excluded.{TrailTable.park},
                    {TrailTable.hazardous} = excluded.{TrailTable.hazardous},
                    {TrailTable.length} = excluded.{TrailTable.length},
                    {TrailTable.vertical} = excluded.{TrailTable.vertical},
                    {TrailTable.difficulty} = excluded.{TrailTable.difficulty},
                    {TrailTable.max_slope} = excluded.{TrailTable.max_slope},
                    {TrailTable.average_slope} = excluded.{TrailTable.average_slope},
                    {TrailTable.steepest_100ft} = excluded.{TrailTable.steepest_100ft},
                    {TrailTable.steepest_150ft} = excluded.{TrailTable.steepest_150ft},
                    {TrailTable.steepest_300ft} = excluded.{TrailTable.steepest_300ft},
                    {TrailTable.steepest_500ft} = excluded.{TrailTable.steepest_500ft},
                    {TrailTable.steepest_1320ft} = excluded.{TrailTable.steepest_1320ft},
                    {TrailTable.steepest_2640ft} = excluded.{TrailTable.steepest_2640ft},
                    {TrailTable.steepest_5280ft} = excluded.{TrailTable.steepest_5280ft}
            """
            params = (
                self.trail_id,
                db_id(self.mountain_id),
                str(round_geometry_precision(self.geometry)),
                str(round_geometry_precision(self.interior_geometry))
                if self.interior_geometry
                else None,
                str(round_geometry_precision(self.route))
                if self.route is not None
                else None,
                self.name,
                self.official_rating,
                self.gladed,
                self.area,
                self.multi_route,
                self.ungroomed,
                self.park,
                self.hazardous,
                self.length,
                self.vertical,
                self.difficulty,
                self.max_slope,
                self.average_slope,
                self.steepest_100ft,
                self.steepest_150ft,
                self.steepest_300ft,
                self.steepest_500ft,
                self.steepest_1320ft,
                self.steepest_2640ft,
                self.steepest_5280ft,
            )
            cur.execute(query, params)

    def delete_from_db(trail_id: str, db_path: str = DATABASE_PATH) -> None:
        """
        Removes a trail from the DB by id.
        """
        with cursor(db_path=db_path) as cur:
            query = f"DELETE FROM Trails WHERE {TrailTable.trail_id} = ?"
            cur.execute(query, (trail_id,))
