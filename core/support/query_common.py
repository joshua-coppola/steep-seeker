from core.datamodels.database import MountainTable
from core.datamodels.region import Region
from core.datamodels.state import State


def name_and_location_where(
    table: str, name_column: str, state: State | None, region: Region | None
) -> tuple[str, list]:
    """
    Builds the WHERE clause shared by the trail-rankings and lift-rankings
    queries: a non-empty name on `table`, plus an optional state (exact
    match) or region (state IN (...)) filter on the joined Mountains row.
    state wins when both are given. Returns (sql, params) for a
    parameterized query.
    """
    clauses = [f'{table}.{name_column} <> ""']
    params: list = []

    if state is not None:
        clauses.append(f"Mountains.{MountainTable.state} = ?")
        params.append(state.value)
    elif region is not None:
        state_values = [s.value for s in region.value]
        placeholders = ",".join("?" * len(state_values))
        clauses.append(f"Mountains.{MountainTable.state} IN ({placeholders})")
        params.extend(state_values)

    return " AND ".join(clauses), params
