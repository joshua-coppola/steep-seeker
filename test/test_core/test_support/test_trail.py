import pytest
from shapely import LineString

from core.connectors.database import cursor
from core.datamodels.database import TrailTable
from core.support.trail import Trail


def test_trail(trail_factory):
    trail = trail_factory()
    assert trail.geometry == LineString([[1, 1, 10], [0, 0, 0]])


def test_trail_length_feet(trail_factory):
    trail = trail_factory(length=100)
    assert trail.length_feet() == round(100 * 3.28084)


def test_trail_vertical_feet(trail_factory):
    trail = trail_factory(vertical=50)
    assert trail.vertical_feet() == round(50 * 3.28084)


def test_trail_from_db(trail_factory, db_path):
    trail = trail_factory()
    with cursor(db_path=db_path) as cur:
        query = f"""
            INSERT INTO Trails (
                {TrailTable.trail_id},
                {TrailTable.mountain_id},
                {TrailTable.geometry},
                {TrailTable.interior_geometry},
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            trail.trail_id,
            trail.mountain_id,
            str(trail.geometry),
            str(trail.interior_geometry),
            trail.name,
            trail.official_rating,
            trail.gladed,
            trail.area,
            trail.ungroomed,
            trail.park,
            trail.length,
            trail.vertical,
            trail.difficulty,
            trail.max_slope,
            trail.average_slope,
            trail.steepest_30m,
            trail.steepest_50m,
            trail.steepest_100m,
            trail.steepest_200m,
            trail.steepest_500m,
            trail.steepest_1000m,
        )
        cur.execute(query, params)

    returned_trail = Trail.from_db(trail.trail_id, db_path=db_path)

    assert trail == returned_trail

    assert Trail.from_db("fake_id", db_path) is None


def test_trail_to_db(trail_factory, db_path):
    trail = trail_factory()
    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Trails"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1

    expected_result = {
        TrailTable.trail_id: "w1000",
        TrailTable.mountain_id: "1",
        TrailTable.geometry: "LINESTRING Z (1 1 10, 0 0 0)",
        TrailTable.interior_geometry: "LINESTRING Z (1 1 10, 0 0 0)",
        TrailTable.route: None,
        TrailTable.name: "Test",
        TrailTable.official_rating: "Expert",
        TrailTable.gladed: 1,
        TrailTable.area: 0,
        TrailTable.ungroomed: 0,
        TrailTable.park: 0,
        TrailTable.length: 1.0,
        TrailTable.vertical: 1.0,
        TrailTable.difficulty: 1.0,
        TrailTable.max_slope: 1.0,
        TrailTable.average_slope: 1.0,
        TrailTable.steepest_30m: 1.0,
        TrailTable.steepest_50m: 1.0,
        TrailTable.steepest_100m: 1.0,
        TrailTable.steepest_200m: 1.0,
        TrailTable.steepest_500m: 1.0,
        TrailTable.steepest_1000m: 1.0,
    }

    assert dict(result[0]) == expected_result

    trail.difficulty = 0.5
    expected_result[TrailTable.difficulty] = 0.5

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        sql_query = "SELECT * FROM Trails"

        result = cur.execute(sql_query).fetchall()

    assert len(result) == 1
    assert dict(result[0]) == expected_result

    trail.name = None

    with pytest.raises(Exception) as exc_info:
        trail.to_db(db_path=db_path)

    assert "fields are missing" in str(exc_info)


def test_trail_to_db_rounds_geometry_precision(trail_factory, db_path):
    trail = trail_factory()
    trail.geometry = LineString([[-72.1234567891, 43.1234567891, 10], [0, 0, 0]])
    trail.interior_geometry = LineString(
        [[-72.1234567891, 43.1234567891, 10], [0, 0, 0]]
    )
    trail.route = LineString([[-72.1234567891, 43.1234567891, 10], [0, 0, 0]])

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = dict(cur.execute("SELECT * FROM Trails").fetchall()[0])

    assert (
        result[TrailTable.geometry] == "LINESTRING Z (-72.123457 43.123457 10, 0 0 0)"
    )
    assert (
        result[TrailTable.interior_geometry]
        == "LINESTRING Z (-72.123457 43.123457 10, 0 0 0)"
    )
    assert result[TrailTable.route] == "LINESTRING Z (-72.123457 43.123457 10, 0 0 0)"


def test_trail_to_db_allows_missing_steepest_pitch(trail_factory, db_path):
    trail = trail_factory()
    # A trail shorter than a given window legitimately has no steepest
    # pitch for it, so these fields should not block saving
    trail.steepest_500m = None
    trail.steepest_1000m = None

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = cur.execute("SELECT * FROM Trails").fetchall()

    assert dict(result[0])[TrailTable.steepest_500m] is None
    assert dict(result[0])[TrailTable.steepest_1000m] is None


def test_trail_to_db_allows_none_interior_geometry_for_line_trail(
    trail_factory, db_path
):
    # OSMProcessor leaves interior_geometry as None for non-area (line)
    # trails -- it's only populated for area trails -- so saving one
    # shouldn't be blocked, and it must round-trip as a real NULL rather
    # than the literal string "None"
    trail = trail_factory(interior_geometry=None)

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = dict(cur.execute("SELECT * FROM Trails").fetchall()[0])

    assert result[TrailTable.interior_geometry] is None

    returned_trail = Trail.from_db(trail.trail_id, db_path=db_path)
    assert returned_trail.interior_geometry is None


def test_trail_to_db_allows_missing_official_rating(trail_factory, db_path):
    # official_rating comes from OSM's piste:difficulty tag, which many
    # real trails simply aren't tagged with
    trail = trail_factory(official_rating=None)

    trail.to_db(db_path=db_path)

    with cursor(db_path=db_path, dict_cursor=True) as cur:
        result = dict(cur.execute("SELECT * FROM Trails").fetchall()[0])

    assert result[TrailTable.official_rating] is None

    returned_trail = Trail.from_db(trail.trail_id, db_path=db_path)
    assert returned_trail.official_rating is None


def test_trail_delete_from_db(trail_factory, db_path):
    trail = trail_factory()
    trail.to_db(db_path=db_path)

    assert Trail.from_db(trail.trail_id, db_path=db_path) is not None

    Trail.delete_from_db(trail.trail_id, db_path=db_path)

    assert Trail.from_db(trail.trail_id, db_path=db_path) is None


def test_trail_delete_from_db_nonexistent_id_is_a_no_op(db_path):
    Trail.delete_from_db("nonexistent", db_path=db_path)
