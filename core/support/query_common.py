from core.datamodels.database import MountainTable
from core.datamodels.region import Region
from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State


def parse_season_passes(value: str | None) -> list[Season_Pass]:
    """
    Turns the comma-joined season_passes column into a list of Season_Pass,
    dropping blanks. Shared by the mountain/trail/lift ranking queries.
    """
    return [Season_Pass(item) for item in (value or "").split(",") if item]


def name_and_location_where(
    table: str,
    name_column: str,
    state: State | None,
    region: Region | None,
    season_pass: Season_Pass | None = None,
) -> tuple[str, list]:
    """
    Builds the WHERE clause shared by the trail-rankings and lift-rankings
    queries: a non-empty name on `table`, plus an optional state (exact
    match) or region (state IN (...)) filter on the joined Mountains row
    (state wins when both are given), and an optional season pass the
    resort must be on. Returns (sql, params) for a parameterized query.
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

    if season_pass is not None:
        # season_passes is comma-joined ("Epic,Ikon"); wrapping both it and
        # the value in commas makes this an exact match on one entry
        clauses.append(
            f"instr(',' || Mountains.{MountainTable.season_passes} || ',', ?) > 0"
        )
        params.append(f",{season_pass.value},")

    return " AND ".join(clauses), params
