from dataclasses import dataclass

from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import MountainTable
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.support.utils import meters_to_feet, round_degrees, round_feet

VALID_SORT_FIELDS = {
    "name",
    "trail_count",
    "lift_count",
    "vertical",
    "difficulty",
    "beginner_friendliness",
}


@dataclass
class MountainSummary:
    """
    Lightweight view of a Mountain for list pages (search, rankings) that
    avoids loading every trail/lift's full geometry the way
    Mountain.from_db does.
    """

    mountain_id: str
    name: str
    state: State
    vertical: int  # feet, converted from the meters Mountain.vertical is stored in
    difficulty: float
    beginner_friendliness: float
    trail_count: int
    lift_count: int
    season_passes: list[Season_Pass]

    def region(self) -> Region:
        return Region.get_region(self.state)


def list_mountains(
    db_path: str = DATABASE_PATH,
    name_query: str | None = None,
    state: State | None = None,
    region: Region | None = None,
    difficulty_min: float = 0,
    difficulty_max: float = 100,
    trail_count_min: float = 0,
    trail_count_max: float = 10_000,
    sort: str = "name",
    order: str = "asc",
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[MountainSummary], int]:
    """
    Returns mountain summaries matching the given filters, sorted and
    paginated. region/trail_count/lift_count aren't stored columns (they're
    computed on Mountain the same way), so filtering/sorting/pagination on
    them happens here in Python rather than in SQL -- the site's mountain
    count is small enough (low hundreds) for that to be cheap.

    Returns (summaries, total_count), where total_count is the number of
    matches before pagination, for building pager UIs.
    """
    if sort not in VALID_SORT_FIELDS:
        sort = "name"
    if order not in ("asc", "desc"):
        order = "asc"

    query = f"""
        SELECT
            m.{MountainTable.mountain_id},
            m.{MountainTable.name},
            m.{MountainTable.state},
            m.{MountainTable.vertical},
            m.{MountainTable.difficulty},
            m.{MountainTable.beginner_friendliness},
            m.{MountainTable.season_passes},
            (SELECT COUNT(*) FROM Trails t WHERE t.mountain_id = m.mountain_id) AS trail_count,
            (SELECT COUNT(*) FROM Lifts l WHERE l.mountain_id = m.mountain_id) AS lift_count
        FROM Mountains m
    """
    with cursor(db_path=db_path) as cur:
        rows = cur.execute(query).fetchall()

    summaries = [
        MountainSummary(
            mountain_id=row[MountainTable.mountain_id],
            name=row[MountainTable.name],
            state=State(row[MountainTable.state]),
            vertical=round_feet(meters_to_feet(row[MountainTable.vertical])),
            difficulty=round_degrees(row[MountainTable.difficulty]),
            beginner_friendliness=round_degrees(
                row[MountainTable.beginner_friendliness]
            ),
            trail_count=row["trail_count"],
            lift_count=row["lift_count"],
            season_passes=[
                Season_Pass(value)
                for value in row[MountainTable.season_passes].split(",")
                if value
            ],
        )
        for row in rows
    ]

    if name_query:
        needle = name_query.strip().lower()
        summaries = [s for s in summaries if needle in s.name.lower()]
    if state is not None:
        summaries = [s for s in summaries if s.state == state]
    if region is not None:
        summaries = [s for s in summaries if s.region() == region]
    summaries = [
        s
        for s in summaries
        if difficulty_min <= s.difficulty <= difficulty_max
        and trail_count_min <= s.trail_count <= trail_count_max
    ]

    summaries.sort(
        key=lambda s: s.name.lower() if sort == "name" else getattr(s, sort),
        reverse=(order == "desc"),
    )

    total_count = len(summaries)

    if limit is not None:
        summaries = summaries[offset : offset + limit]

    return summaries, total_count
