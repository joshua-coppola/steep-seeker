from core.connectors.database import DATABASE_PATH, cursor
from core.datamodels.database import BlacklistTable


def add_to_blacklist(
    mountain_id: str, item_id: str, db_path: str = DATABASE_PATH
) -> None:
    """
    Marks a trail/lift id as blacklisted for a mountain, so a future
    refresh from OSM knows to skip re-adding it.
    """
    with cursor(db_path=db_path) as cur:
        query = f"""
            INSERT INTO Blacklist ({BlacklistTable.item_id}, {BlacklistTable.mountain_id})
            VALUES (?, ?)
            ON CONFLICT({BlacklistTable.item_id}) DO UPDATE SET
                {BlacklistTable.mountain_id} = excluded.{BlacklistTable.mountain_id}
        """
        params = (item_id, mountain_id)
        cur.execute(query, params)


def is_blacklisted(
    mountain_id: str, item_id: str, db_path: str = DATABASE_PATH
) -> bool:
    """
    Returns whether a trail/lift id has been blacklisted for a mountain.
    """
    with cursor(db_path=db_path) as cur:
        query = f"""
            SELECT 1 FROM Blacklist
            WHERE {BlacklistTable.mountain_id} = ? AND {BlacklistTable.item_id} = ?
        """
        params = (mountain_id, item_id)
        result = cur.execute(query, params).fetchone()

    return result is not None
