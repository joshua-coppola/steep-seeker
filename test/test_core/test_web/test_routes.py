import pytest

from core.datamodels.state import State
from core.web.app import create_app


@pytest.fixture
def client(db_path):
    app = create_app(db_path=db_path)
    app.testing = True
    return app.test_client()


def test_index_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Steep Seeker" in response.data


def test_about_returns_ok(client):
    response = client.get("/about")

    assert response.status_code == 200
    assert b"About" in response.data


def _trails(trail_factory, mountain_id, count):
    return {
        f"{mountain_id}-t{i}": trail_factory(
            trail_id=f"{mountain_id}-t{i}", mountain_id=mountain_id
        )
        for i in range(count)
    }


@pytest.fixture
def seeded_client(client, db_path, mountain_factory, trail_factory):
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        difficulty=40,
        beginner_friendliness=5,
        trails=_trails(trail_factory, "1", 3),
        lifts={},
    ).to_db(db_path)
    mountain_factory(
        mountain_id="2",
        name="Killington",
        state=State.VERMONT,
        difficulty=70,
        beginner_friendliness=2,
        trails=_trails(trail_factory, "2", 10),
        lifts={},
    ).to_db(db_path)
    mountain_factory(
        mountain_id="3",
        name="Alta",
        state=State.UTAH,
        difficulty=90,
        beginner_friendliness=1,
        trails=_trails(trail_factory, "3", 5),
        lifts={},
    ).to_db(db_path)

    return client


def test_search_returns_all_mountains_by_default(seeded_client):
    response = seeded_client.get("/search")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley" in body
    assert "Killington" in body
    assert "Alta" in body


def test_search_filters_by_name(seeded_client):
    response = seeded_client.get("/search?q=Kill")

    body = response.data.decode()
    assert "Killington" in body
    assert "Bolton Valley" not in body


def test_search_filters_by_state(seeded_client):
    response = seeded_client.get("/search?location=UT")

    body = response.data.decode()
    assert "Alta" in body
    assert "Killington" not in body


def test_search_paginates(seeded_client):
    response = seeded_client.get("/search?limit=1&sort=name&order=asc")

    body = response.data.decode()
    assert "Alta" in body
    assert "Bolton Valley" not in body
    assert "Next Page" in body


def test_rankings_defaults_to_difficulty_desc(seeded_client):
    response = seeded_client.get("/rankings")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Alta") < body.index("Killington") < body.index("Bolton Valley")


def test_rankings_filters_by_region(seeded_client):
    response = seeded_client.get("/rankings?region=northeast")

    body = response.data.decode()
    assert "Bolton Valley" in body
    assert "Killington" in body
    assert "Alta" not in body


def test_rankings_filters_by_state(seeded_client):
    response = seeded_client.get("/rankings?state=UT")

    body = response.data.decode()
    assert "Alta" in body
    assert "Killington" not in body


def test_rankings_beginner_sort(seeded_client):
    response = seeded_client.get("/rankings?sort=beginner&order=desc")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Bolton Valley") < body.index("Killington") < body.index("Alta")


@pytest.fixture
def ranked_client(client, db_path, mountain_factory, trail_factory, lift_factory):
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={
            "1-a": trail_factory(
                trail_id="1-a", mountain_id="1", name="Trail A", difficulty=80
            ),
        },
        lifts={
            "1-a": lift_factory(
                lift_id="1-a",
                mountain_id="1",
                name="Lift A",
                vertical=500,
                length=2000,
                average_slope=25,
            ),
        },
    ).to_db(db_path)
    mountain_factory(
        mountain_id="2",
        name="Alta",
        state=State.UTAH,
        trails={
            "2-b": trail_factory(
                trail_id="2-b", mountain_id="2", name="Trail B", difficulty=95
            ),
        },
        lifts={
            "2-b": lift_factory(
                lift_id="2-b",
                mountain_id="2",
                name="Lift B",
                vertical=800,
                length=2500,
                average_slope=20,
            ),
        },
    ).to_db(db_path)

    return client


def test_trail_rankings_defaults_to_difficulty_desc(ranked_client):
    response = ranked_client.get("/trail-rankings")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Trail B") < body.index("Trail A")


def test_trail_rankings_filters_by_state(ranked_client):
    response = ranked_client.get("/trail-rankings?state=UT")

    body = response.data.decode()
    assert "Trail B" in body
    assert "Trail A" not in body


def test_lift_rankings_defaults_to_vertical_desc(ranked_client):
    response = ranked_client.get("/lift-rankings")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Lift B") < body.index("Lift A")


def test_lift_rankings_sorts_by_average_slope(ranked_client):
    response = ranked_client.get("/lift-rankings?sort=average_slope")

    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Lift A") < body.index("Lift B")


def test_lift_rankings_filters_by_region(ranked_client):
    response = ranked_client.get("/lift-rankings?region=west")

    body = response.data.decode()
    assert "Lift B" in body
    assert "Lift A" not in body
