from dataclasses import dataclass

from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import LiftTable, MountainTable
from core.datamodels.region import Region
from core.datamodels.state import State
from core.support.utils import meters_to_feet, round_degrees, round_feet

VALID_SORT_FIELDS = {
    "vertical",
    "length",
    "average_slope",
    "occupancy",
    "capacity",
    "detachable",
    "bubble",
    "heating",
}


@dataclass
class LiftSummary:
    """
    Lightweight view of a Lift for the lift-rankings list page, joined
    with its mountain's name/state. Display-rounded: vertical/length to the
    nearest foot (Lift stores them in meters); average_slope (degrees, not
    a distance unit) to the nearest 0.1 degree.
    """

    lift_id: str
    name: str
    resort_name: str
    state: State
    vertical: int | None
    length: int | None
    average_slope: float | None
    occupancy: int | None
    capacity: int | None
    detachable: bool | None
    bubble: bool | None
    heating: bool | None


def _where_clause(state: State | None, region: Region | None) -> tuple[str, list]:
    where_clauses = [f'Lifts.{LiftTable.name} <> ""']
    params: list = []

    if state is not None:
        where_clauses.append(f"Mountains.{MountainTable.state} = ?")
        params.append(state.value)
    elif region is not None:
        state_values = [s.value for s in region.value]
        placeholders = ",".join("?" * len(state_values))
        where_clauses.append(f"Mountains.{MountainTable.state} IN ({placeholders})")
        params.extend(state_values)

    return " AND ".join(where_clauses), params


def list_lifts(
    db_path: str = DATABASE_PATH,
    state: State | None = None,
    region: Region | None = None,
    sort: str = "vertical",
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[LiftSummary], int]:
    """
    Returns lift summaries (joined with resort name/state) for lifts
    matching the given region/state filter (state takes priority when both
    are given), sorted descending by `sort` -- a real Lifts column, so
    filtering/sorting/pagination all happen in SQL -- and paginated. Lifts
    with no name are excluded, matching the old site's behavior.

    Returns (summaries, total_count), where total_count is the number of
    matches before pagination, for building pager UIs.
    """
    if sort not in VALID_SORT_FIELDS:
        sort = "vertical"

    where_sql, params = _where_clause(state, region)

    with cursor(db_path=db_path) as cur:
        count_query = f"""
            SELECT COUNT(*)
            FROM Lifts
            INNER JOIN Mountains
                ON Lifts.{LiftTable.mountain_id} = Mountains.{MountainTable.mountain_id}
            WHERE {where_sql}
        """
        total_count = cur.execute(count_query, params).fetchone()[0]

        query = f"""
            SELECT
                Lifts.{LiftTable.lift_id},
                Lifts.{LiftTable.name},
                Mountains.{MountainTable.name} AS resort_name,
                Mountains.{MountainTable.state} AS resort_state,
                Lifts.{LiftTable.vertical},
                Lifts.{LiftTable.length},
                Lifts.{LiftTable.average_slope},
                Lifts.{LiftTable.occupancy},
                Lifts.{LiftTable.capacity},
                Lifts.{LiftTable.detachable},
                Lifts.{LiftTable.bubble},
                Lifts.{LiftTable.heating}
            FROM Lifts
            INNER JOIN Mountains
                ON Lifts.{LiftTable.mountain_id} = Mountains.{MountainTable.mountain_id}
            WHERE {where_sql}
            ORDER BY Lifts.{sort} DESC
            LIMIT ? OFFSET ?
        """
        query_params = [*params, -1 if limit is None else limit, offset]
        rows = cur.execute(query, query_params).fetchall()

    def _bool_or_none(value) -> bool | None:
        return None if value is None else bool(value)

    summaries = [
        LiftSummary(
            lift_id=row[LiftTable.lift_id],
            name=row[LiftTable.name],
            resort_name=row["resort_name"],
            state=State(row["resort_state"]),
            vertical=round_feet(meters_to_feet(row[LiftTable.vertical])),
            length=round_feet(meters_to_feet(row[LiftTable.length])),
            average_slope=round_degrees(row[LiftTable.average_slope]),
            occupancy=row[LiftTable.occupancy],
            capacity=row[LiftTable.capacity],
            detachable=_bool_or_none(row[LiftTable.detachable]),
            bubble=_bool_or_none(row[LiftTable.bubble]),
            heating=_bool_or_none(row[LiftTable.heating]),
        )
        for row in rows
    ]

    return summaries, total_count
