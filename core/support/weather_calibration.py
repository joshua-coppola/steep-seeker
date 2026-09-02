import bisect
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import (
    MountainTable,
    TrailTable,
    WeatherCalibrationTable,
)
from core.support.utils import (
    get_mountain_rating,
    get_trail_difficulty,
    surface_difficulty_bonus,
)

# Checked-in bootstrap snapshot, used until the first recalibration writes a
# real row (keeps a fresh DB - and the test suite - rating resorts sensibly).
DEFAULT_CALIBRATION_PATH = "config/weather_calibration.json"


@dataclass
class WeatherCalibration:
    """
    A frozen snapshot of the resort population's averaged winter weather, the
    reference every resort's weather modifier is scored against. Each metric is
    stored as the sorted list of per-resort values; `modifier` scores a resort
    by its percentile rank within those lists.

    Replaces the hardcoded mean / 2-sigma constants that used to live on
    `Weather`: rebuild it from the current population with `recalibrate` (wired
    to the management panel's Bulk Operations page) instead of editing code
    every year.
    """

    icy_days: list[float]
    rain: list[float]
    snow: list[float]
    n_resorts: int
    created: str

    @classmethod
    def from_population(cls, rows, created: str | None = None) -> "WeatherCalibration":
        """
        Build a calibration from an iterable of (icy_days, rain, snow) tuples,
        one per resort. Each metric's values are stored sorted ascending.
        """
        columns = list(zip(*rows, strict=True))
        if not columns or not columns[0]:
            raise ValueError(
                "cannot build a WeatherCalibration from an empty population"
            )

        icy_days, rain, snow = (sorted(float(v) for v in col) for col in columns)
        return cls(
            icy_days=icy_days,
            rain=rain,
            snow=snow,
            n_resorts=len(icy_days),
            created=created or datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _rank(sorted_values: list[float], x: float) -> float:
        """
        Percentile rank of `x` within `sorted_values` (ascending), in [0, 1],
        linearly interpolated between neighbours and saturating at the ends so
        an out-of-range value (e.g. a new record) maxes out rather than
        overflowing.
        """
        if x <= sorted_values[0]:
            return 0.0
        if x >= sorted_values[-1]:
            return 1.0

        hi = bisect.bisect_left(sorted_values, x)  # sorted_values[hi-1] <= x <= [hi]
        span = sorted_values[hi] - sorted_values[hi - 1]
        frac = 0.0 if span == 0 else (x - sorted_values[hi - 1]) / span
        return (hi - 1 + frac) / (len(sorted_values) - 1)

    def modifier(self, weather: dict[str, float]) -> float:
        """
        Weather difficulty modifier (0-6 degrees) for a resort, from a dict of
        averaged winter metrics (as `Weather.get()` returns). Each metric
        contributes up to 2 degrees by its percentile rank in the population;
        snow is inverted, since more snow means better (easier) conditions.
        """
        icy = self._rank(self.icy_days, weather["icy_days"])
        rain = self._rank(self.rain, weather["rain"])
        snow = self._rank(self.snow, weather["snow"])
        return 2 * icy + 2 * rain + 2 * (1 - snow)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "WeatherCalibration":
        return cls(**json.loads(text))

    def _write(self, cur: sqlite3.Cursor) -> None:
        """Persist as the single WeatherCalibration row (id = 1) via `cur`."""
        cur.execute(
            f"""
            INSERT OR REPLACE INTO WeatherCalibration (
                {WeatherCalibrationTable.id},
                {WeatherCalibrationTable.created},
                {WeatherCalibrationTable.n_resorts},
                {WeatherCalibrationTable.icy_days},
                {WeatherCalibrationTable.rain},
                {WeatherCalibrationTable.snow}
            ) VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                self.created,
                self.n_resorts,
                json.dumps(self.icy_days),
                json.dumps(self.rain),
                json.dumps(self.snow),
            ),
        )

    def save(self, db_path: str = DATABASE_PATH) -> None:
        with cursor(db_path) as cur:
            self._write(cur)

    @classmethod
    def load(cls, db_path: str = DATABASE_PATH) -> "WeatherCalibration":
        """
        The stored calibration, or the checked-in bootstrap snapshot
        (`config/weather_calibration.json`) when no row exists yet.
        """
        with cursor(db_path) as cur:
            try:
                row = cur.execute(
                    f"""
                    SELECT {WeatherCalibrationTable.icy_days},
                           {WeatherCalibrationTable.rain},
                           {WeatherCalibrationTable.snow},
                           {WeatherCalibrationTable.n_resorts},
                           {WeatherCalibrationTable.created}
                    FROM WeatherCalibration
                    WHERE {WeatherCalibrationTable.id} = 1
                    """
                ).fetchone()
            except sqlite3.OperationalError:
                row = None  # table not created on this database yet

        if row is not None:
            return cls(
                icy_days=json.loads(row[WeatherCalibrationTable.icy_days]),
                rain=json.loads(row[WeatherCalibrationTable.rain]),
                snow=json.loads(row[WeatherCalibrationTable.snow]),
                n_resorts=row[WeatherCalibrationTable.n_resorts],
                created=row[WeatherCalibrationTable.created],
            )

        return cls.from_json(Path(DEFAULT_CALIBRATION_PATH).read_text())


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _recovered_modifier(trail: sqlite3.Row) -> float:
    """The weather modifier baked into an already-rated trail's difficulty."""
    return (
        trail[TrailTable.difficulty]
        - trail[TrailTable.steepest_30m]
        - surface_difficulty_bonus(
            bool(trail[TrailTable.gladed]), bool(trail[TrailTable.ungroomed])
        )
    )


def recalibrate(db_path: str = DATABASE_PATH) -> dict:
    """
    Rebuild the WeatherCalibration from the current Mountains rows, then re-rate
    every trail's difficulty (and each mountain's difficulty /
    beginner_friendliness) against the new snapshot, so all resorts share one
    calibration. `vertical` is untouched -- weather doesn't move elevation.

    All reads and writes run in one transaction. Returns a summary: resorts and
    trails touched, `rerated_mountain_ids` (the resorts whose trail difficulties
    changed, so the caller can regenerate their maps), and the population-mean
    weather modifier before and after.
    """
    with cursor(db_path) as cur:
        mountains = cur.execute(
            f"""
            SELECT {MountainTable.mountain_id} AS mountain_id,
                   {MountainTable.average_icy_days} AS icy_days,
                   {MountainTable.average_rain} AS rain,
                   {MountainTable.average_snow} AS snow
            FROM Mountains
            WHERE {MountainTable.average_icy_days} IS NOT NULL
              AND {MountainTable.average_rain} IS NOT NULL
              AND {MountainTable.average_snow} IS NOT NULL
            """
        ).fetchall()

        calibration = WeatherCalibration.from_population(
            (m["icy_days"], m["rain"], m["snow"]) for m in mountains
        )
        calibration._write(cur)

        before: list[float] = []
        after: list[float] = []
        rerated_mountain_ids: list[str] = []
        trail_updates: list[tuple[float | None, str]] = []
        mountain_updates: list[tuple[float, float, str]] = []

        for mountain in mountains:
            trails = cur.execute(
                f"""
                SELECT {TrailTable.trail_id}, {TrailTable.steepest_30m},
                       {TrailTable.gladed}, {TrailTable.ungroomed},
                       {TrailTable.length}, {TrailTable.difficulty}
                FROM Trails WHERE {TrailTable.mountain_id} = ?
                """,
                (mountain["mountain_id"],),
            ).fetchall()
            if not trails:
                continue
            rerated_mountain_ids.append(mountain["mountain_id"])

            rated = [
                trail
                for trail in trails
                if trail[TrailTable.difficulty] is not None
                and trail[TrailTable.steepest_30m] is not None
            ]
            if rated:
                before.append(_recovered_modifier(rated[0]))

            modifier = calibration.modifier(
                {
                    "icy_days": mountain["icy_days"],
                    "rain": mountain["rain"],
                    "snow": mountain["snow"],
                }
            )
            after.append(modifier)

            rerated: list[float] = []
            for trail in trails:
                difficulty = get_trail_difficulty(
                    trail[TrailTable.steepest_30m],
                    bool(trail[TrailTable.gladed]),
                    bool(trail[TrailTable.ungroomed]),
                    modifier,
                )
                trail_updates.append((difficulty, trail[TrailTable.trail_id]))
                length = trail[TrailTable.length]
                if difficulty is not None and length is not None and length > 100:
                    rerated.append(difficulty)

            difficulty, beginner_friendliness = get_mountain_rating(rerated)
            if difficulty is not None:
                mountain_updates.append(
                    (difficulty, beginner_friendliness, mountain["mountain_id"])
                )

        cur.executemany(
            f"UPDATE Trails SET {TrailTable.difficulty} = ? "
            f"WHERE {TrailTable.trail_id} = ?",
            trail_updates,
        )
        cur.executemany(
            f"""
            UPDATE Mountains SET
                {MountainTable.difficulty} = ?,
                {MountainTable.beginner_friendliness} = ?
            WHERE {MountainTable.mountain_id} = ?
            """,
            mountain_updates,
        )

    return {
        "n_resorts": len(mountains),
        "n_trails_rerated": len(trail_updates),
        "rerated_mountain_ids": rerated_mountain_ids,
        "mean_modifier_before": _mean(before),
        "mean_modifier_after": _mean(after),
    }
