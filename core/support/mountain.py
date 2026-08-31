from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Self

from shapely import Point, wkt

from core.connectors.database import DATABASE_PATH, cursor, db_id
from core.connectors.weather_api import Weather
from core.datamodels.database import (
    BlacklistTable,
    LiftTable,
    MountainTable,
    TrailTable,
)
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.osm.osm_processor import OSMProcessor
from core.support.lift import Lift
from core.support.trail import Trail
from core.support.utils import (
    get_mountain_rating,
    get_trail_difficulty,
    meters_to_feet,
    round_feet,
    round_geometry_precision,
)


@dataclass
class Mountain:
    """
    Mountain dataclass that contains all information about a specific
    mountain. An existing mountain can be loaded from the DB with from_db,
    and a new or updated mountain can be saved back to the DB with to_db.
    """

    mountain_id: str
    name: str
    state: State
    direction: str
    coordinates: Point
    season_passes: list[Season_Pass] | None = field(default_factory=list)
    url: str | None = None
    vertical: int | None = None
    difficulty: float | None = None
    beginner_friendliness: float | None = None
    average_icy_days: float | None = None
    average_snow: float | None = None
    average_rain: float | None = None
    last_updated: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    trails: dict[str, Trail] | None = field(default_factory=dict)
    lifts: dict[str, Lift] | None = field(default_factory=dict)

    def region(self) -> Region:
        """
        Returns the geographic region the mountain is a part of
        (NORTHEAST, SOUTHEAST, MIDWEST, WEST)
        """
        return Region.get_region(self.state)

    def vertical_feet(self) -> int | None:
        """
        Returns vertical drop in feet, for displa. Vertical is stored
        in meters.
        """
        return round_feet(meters_to_feet(self.vertical))

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

    def rotate_clockwise(self) -> None:
        """
        Rotates the map's orientation 90 degrees clockwise.
        """
        order = ["n", "e", "s", "w"]
        self.direction = order[(order.index(self.direction) + 1) % len(order)]

    def rotate_counterclockwise(self) -> None:
        """
        Rotates the map's orientation 90 degrees counter-clockwise.
        """
        order = ["n", "e", "s", "w"]
        self.direction = order[(order.index(self.direction) - 1) % len(order)]

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
        self.trails[trail.trail_id] = trail

    def add_lift(self, lift: Lift) -> None:
        """
        Inserts a new trail into lifts dict
        """
        self.lifts[lift.lift_id] = lift

    def from_db(
        mountain_id: str,
        db_path: str = DATABASE_PATH,
        include_trails: bool = True,
        include_lifts: bool = True,
    ) -> Self:
        """
        Gets mountain data from database and returns a Mountain object
        """
        # sqlite3 can't bind UUID objects directly (mountain_id is a UUID
        # for OSM-derived mountains); normalize once and reuse below
        db_mountain_id = db_id(mountain_id)

        with cursor(db_path=db_path) as cur:
            query = "SELECT * from Mountains WHERE mountain_id = ?"
            params = (db_mountain_id,)
            result = cur.execute(query, params).fetchone()

        if not result:
            return None

        result = dict(result)
        result[MountainTable.state] = State(result[MountainTable.state])
        result[MountainTable.coordinates] = wkt.loads(result[MountainTable.coordinates])
        result[MountainTable.season_passes] = (
            [
                Season_Pass(value)
                for value in result[MountainTable.season_passes].split(",")
            ]
            if result[MountainTable.season_passes]
            else []
        )
        result[MountainTable.last_updated] = datetime.fromisoformat(
            result[MountainTable.last_updated]
        )

        if include_trails:
            with cursor(db_path=db_path) as cur:
                query = f"SELECT {TrailTable.trail_id} from Trails WHERE {TrailTable.mountain_id} = ?"
                params = (db_mountain_id,)
                trails_result = cur.execute(query, params).fetchall()

            if trails_result:
                result[MountainTable.trails] = {
                    trail[TrailTable.trail_id]: Trail.from_db(
                        trail[TrailTable.trail_id], db_path=db_path
                    )
                    for trail in trails_result
                }

        if include_lifts:
            with cursor(db_path=db_path) as cur:
                query = f"SELECT {LiftTable.lift_id} from Lifts WHERE {LiftTable.mountain_id} = ?"
                params = (db_mountain_id,)
                lifts_result = cur.execute(query, params).fetchall()

            if lifts_result:
                result[MountainTable.lifts] = {
                    lift[LiftTable.lift_id]: Lift.from_db(
                        lift[LiftTable.lift_id], db_path=db_path
                    )
                    for lift in lifts_result
                }

        return Mountain(**result)

    def from_name(
        name: str,
        state: State,
        db_path: str = DATABASE_PATH,
        include_trails: bool = True,
        include_lifts: bool = True,
    ) -> Self:
        """
        Looks up a mountain by (state, name) -- used by routes like
        /interactive-map/<state>/<name> that don't carry a mountain_id --
        and returns the same Mountain object from_db would, or None if no
        mountain matches.
        """
        with cursor(db_path=db_path) as cur:
            query = f"SELECT {MountainTable.mountain_id} from Mountains WHERE {MountainTable.state} = ? AND {MountainTable.name} = ?"
            params = (state.value, name)
            result = cur.execute(query, params).fetchone()

        if not result:
            return None

        return Mountain.from_db(
            result[MountainTable.mountain_id],
            db_path=db_path,
            include_trails=include_trails,
            include_lifts=include_lifts,
        )

    def to_db(self, db_path: str = DATABASE_PATH) -> None:
        """
        Updates DB record with the values in the dataclass
        """
        # check that all fields have been populated before saving
        missing_fields = [f.name for f in fields(self) if getattr(self, f.name) is None]
        if len(missing_fields) > 0:
            raise ValueError(f"The following fields are missing: {missing_fields}")

        season_passes = ",".join(
            [season_pass.value for season_pass in self.season_passes]
        )

        with cursor(db_path=db_path) as cur:
            query = f"""
                INSERT INTO Mountains (
                    {MountainTable.mountain_id},
                    {MountainTable.name},
                    {MountainTable.state},
                    {MountainTable.direction},
                    {MountainTable.coordinates},
                    {MountainTable.season_passes},
                    {MountainTable.vertical},
                    {MountainTable.difficulty},
                    {MountainTable.beginner_friendliness},
                    {MountainTable.average_icy_days},
                    {MountainTable.average_snow},
                    {MountainTable.average_rain},
                    {MountainTable.last_updated},
                    {MountainTable.url}
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({MountainTable.mountain_id}) DO UPDATE SET
                    {MountainTable.name} = excluded.{MountainTable.name},
                    {MountainTable.state} = excluded.{MountainTable.state},
                    {MountainTable.direction} = excluded.{MountainTable.direction},
                    {MountainTable.coordinates} = excluded.{MountainTable.coordinates},
                    {MountainTable.season_passes} = excluded.{MountainTable.season_passes},
                    {MountainTable.vertical} = excluded.{MountainTable.vertical},
                    {MountainTable.difficulty} = excluded.{MountainTable.difficulty},
                    {MountainTable.beginner_friendliness} = excluded.{MountainTable.beginner_friendliness},
                    {MountainTable.average_icy_days} = excluded.{MountainTable.average_icy_days},
                    {MountainTable.average_snow} = excluded.{MountainTable.average_snow},
                    {MountainTable.average_rain} = excluded.{MountainTable.average_rain},
                    {MountainTable.last_updated} = excluded.{MountainTable.last_updated},
                    {MountainTable.url} = excluded.{MountainTable.url}
            """
            params = (
                db_id(self.mountain_id),
                self.name,
                self.state.value,
                self.direction,
                str(round_geometry_precision(self.coordinates)),
                season_passes,
                self.vertical,
                self.difficulty,
                self.beginner_friendliness,
                self.average_icy_days,
                self.average_snow,
                self.average_rain,
                self.last_updated.isoformat(),
                self.url,
            )
            cur.execute(query, params)

        for trail_id in self.trails:
            self.trails[trail_id].to_db(db_path)

        for lift_id in self.lifts:
            self.lifts[lift_id].to_db(db_path)

    @staticmethod
    def _trail_ids_owned_elsewhere(
        trail_ids, mountain_id: str, db_path: str = DATABASE_PATH
    ) -> set[str]:
        """
        Returns the subset of trail_ids already stored in the DB under a
        different mountain. Trail ids are OSM element ids and globally
        unique, so an overlap means the trail genuinely belongs to the
        other ski area (resort bounding boxes routinely overlap, and a
        trail near a boundary lands in both extracts). The first area to
        claim a trail keeps it; from_osm drops the rest before elevation
        lookup, so they never enter the API batch, the mountain's
        vertical/difficulty, or Trail.to_db's ON CONFLICT reassignment.
        """
        trail_ids = list(trail_ids)
        if not trail_ids:
            return set()

        placeholders = ",".join("?" * len(trail_ids))
        with cursor(db_path=db_path) as cur:
            rows = cur.execute(
                f"""
                SELECT {TrailTable.trail_id} FROM Trails
                WHERE {TrailTable.trail_id} IN ({placeholders})
                    AND {TrailTable.mountain_id} != ?
                """,
                (*trail_ids, db_id(mountain_id)),
            ).fetchall()

        return {row[TrailTable.trail_id] for row in rows}

    def clear_trails_and_lifts(mountain_id: str, db_path: str = DATABASE_PATH) -> None:
        """
        Removes all trails and lifts belonging to a mountain, without
        touching the mountain row itself or its blacklist entries. Used
        before a refresh rebuilds the trail/lift set from a re-parsed OSM
        file, so trails/lifts no longer present in the new parse don't
        linger as stale rows.
        """
        with cursor(db_path=db_path) as cur:
            cur.execute(
                f"DELETE FROM Trails WHERE {TrailTable.mountain_id} = ?",
                (mountain_id,),
            )
            cur.execute(
                f"DELETE FROM Lifts WHERE {LiftTable.mountain_id} = ?",
                (mountain_id,),
            )

    def delete_from_db(mountain_id: str, db_path: str = DATABASE_PATH) -> None:
        """
        Removes a mountain and all of its trails/lifts/blacklist entries
        from the DB. The schema declares ON DELETE CASCADE for these, but
        sqlite3 doesn't enforce foreign keys unless "PRAGMA foreign_keys =
        ON" is set per-connection (it isn't here), so each table is
        cleared explicitly instead of relying on that cascade.
        """
        Mountain.clear_trails_and_lifts(mountain_id, db_path)

        with cursor(db_path=db_path) as cur:
            cur.execute(
                f"DELETE FROM Blacklist WHERE {BlacklistTable.mountain_id} = ?",
                (mountain_id,),
            )
            cur.execute(
                f"DELETE FROM Mountains WHERE {MountainTable.mountain_id} = ?",
                (mountain_id,),
            )

    def from_osm(
        filename: str,
        season_passes: list[Season_Pass],
        url: str,
        mountain_id: str | None = None,
        db_path: str = DATABASE_PATH,
    ) -> Self:
        """
        Gets mountain data from the provided OSM file and returns a
        Mountain object. Pass the existing mountain_id when re-parsing a
        file for a mountain that's already in the DB (a refresh) so the
        reloaded trails/lifts attach to the same mountain row instead of
        the deterministic ID OSMProcessor would otherwise derive fresh
        from the file's (possibly slightly shifted) center coordinates.

        Trails already owned by another mountain in db_path are dropped
        from the parse before any elevation lookup (see
        _trail_ids_owned_elsewhere).
        """
        processor = OSMProcessor(filename, mountain_id=mountain_id)

        for trail_id in Mountain._trail_ids_owned_elsewhere(
            processor.trails, processor.mountain_id, db_path
        ):
            del processor.trails[trail_id]

        mountain = Mountain(
            mountain_id=processor.mountain_id,
            name=filename.split("/")[-1].split(".osm")[0],
            state=processor.get_state(),
            direction=processor.get_direction(),
            coordinates=processor.get_center(),
            season_passes=season_passes,
            trails=processor.get_trails(),
            lifts=processor.get_lifts(),
            url=url,
        )

        elevation_set = set()
        for trail_id in mountain.trails:
            trail = mountain.trails[trail_id]
            if trail.area:
                elevation_set.update(
                    coord[2] for coord in trail.geometry.exterior.coords
                )
                elevation_set.update(point.z for point in trail.interior_geometry.geoms)
            else:
                elevation_set.update(coord[2] for coord in trail.geometry.coords)

        mountain.vertical = int(max(elevation_set) - min(elevation_set))

        weather = Weather().get(mountain.coordinates)

        mountain.average_icy_days = weather["icy_days"]
        mountain.average_rain = weather["rain"]
        mountain.average_snow = weather["snow"]

        weather_modifier = Weather.get_modifier(weather)
        for trail in mountain.trails.values():
            trail.difficulty = get_trail_difficulty(
                trail.steepest_30m, trail.gladed, trail.ungroomed, weather_modifier
            )

        # only rate the mountain off trails long enough to be meaningful
        rated_trail_difficulties = [
            trail.difficulty
            for trail in mountain.trails.values()
            if trail.length > 100 and trail.difficulty is not None
        ]
        mountain.difficulty, mountain.beginner_friendliness = get_mountain_rating(
            rated_trail_difficulties
        )

        return mountain
