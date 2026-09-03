from dataclasses import dataclass

from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import MountainTable, TrailTable
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.query_common import name_and_location_where, parse_season_passes
from core.support.utils import meters_to_feet, round_degrees, round_feet

VALID_SORT_FIELDS = {
    "length",
    "difficulty",
    "max_slope",
    "average_slope",
    "steepest_30m",
    "steepest_50m",
    "steepest_100m",
    "steepest_200m",
    "steepest_500m",
    "steepest_1000m",
}


@dataclass
class TrailSummary:
    """
    Lightweight view of a Trail for the trail-rankings list page, joined
    with its mountain's name/state. Display-rounded: length to the nearest
    foot (Trail stores it in meters); difficulty/max_slope/average_slope/
    steepest_Xm (degrees, not a distance unit) to the nearest 0.1 degree.
    """

    trail_id: str
    name: str
    resort_name: str
    state: State
    season_passes: list[Season_Pass]
    gladed: bool
    ungroomed: bool
    length: int | None
    difficulty: float | None
    max_slope: float | None
    average_slope: float | None
    steepest_30m: float | None
    steepest_50m: float | None
    steepest_100m: float | None
    steepest_200m: float | None
    steepest_500m: float | None
    steepest_1000m: float | None


def list_trails(
    db_path: str = DATABASE_PATH,
    state: State | None = None,
    region: Region | None = None,
    sort: str = "difficulty",
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[TrailSummary], int]:
    """
    Returns trail summaries (joined with resort name/state) for trails
    matching the given region/state filter (state takes priority when both
    are given), sorted descending by `sort`, and paginated.

    Returns (summaries, total_count), where total_count is the number of
    matches before pagination, for building pager UIs.
    """
    if sort not in VALID_SORT_FIELDS:
        sort = "difficulty"

    where_sql, params = name_and_location_where(
        "Trails", TrailTable.name, state, region
    )

    with cursor(db_path=db_path) as cur:
        count_query = f"""
            SELECT COUNT(*)
            FROM Trails
            INNER JOIN Mountains
                ON Trails.{TrailTable.mountain_id} = Mountains.{MountainTable.mountain_id}
            WHERE {where_sql}
        """
        total_count = cur.execute(count_query, params).fetchone()[0]

        query = f"""
            SELECT
                Trails.{TrailTable.trail_id},
                Trails.{TrailTable.name},
                Mountains.{MountainTable.name} AS resort_name,
                Mountains.{MountainTable.state} AS resort_state,
                Mountains.{MountainTable.season_passes} AS resort_season_passes,
                Trails.{TrailTable.gladed},
                Trails.{TrailTable.ungroomed},
                Trails.{TrailTable.length},
                Trails.{TrailTable.difficulty},
                Trails.{TrailTable.max_slope},
                Trails.{TrailTable.average_slope},
                Trails.{TrailTable.steepest_30m},
                Trails.{TrailTable.steepest_50m},
                Trails.{TrailTable.steepest_100m},
                Trails.{TrailTable.steepest_200m},
                Trails.{TrailTable.steepest_500m},
                Trails.{TrailTable.steepest_1000m}
            FROM Trails
            INNER JOIN Mountains
                ON Trails.{TrailTable.mountain_id} = Mountains.{MountainTable.mountain_id}
            WHERE {where_sql}
            ORDER BY Trails.{sort} DESC
            LIMIT ? OFFSET ?
        """
        query_params = [*params, -1 if limit is None else limit, offset]
        rows = cur.execute(query, query_params).fetchall()

    summaries = [
        TrailSummary(
            trail_id=row[TrailTable.trail_id],
            name=row[TrailTable.name],
            resort_name=row["resort_name"],
            state=State(row["resort_state"]),
            season_passes=parse_season_passes(row["resort_season_passes"]),
            gladed=bool(row[TrailTable.gladed]),
            ungroomed=bool(row[TrailTable.ungroomed]),
            length=round_feet(meters_to_feet(row[TrailTable.length])),
            difficulty=round_degrees(row[TrailTable.difficulty]),
            max_slope=round_degrees(row[TrailTable.max_slope]),
            average_slope=round_degrees(row[TrailTable.average_slope]),
            steepest_30m=round_degrees(row[TrailTable.steepest_30m]),
            steepest_50m=round_degrees(row[TrailTable.steepest_50m]),
            steepest_100m=round_degrees(row[TrailTable.steepest_100m]),
            steepest_200m=round_degrees(row[TrailTable.steepest_200m]),
            steepest_500m=round_degrees(row[TrailTable.steepest_500m]),
            steepest_1000m=round_degrees(row[TrailTable.steepest_1000m]),
        )
        for row in rows
    ]

    return summaries, total_count
