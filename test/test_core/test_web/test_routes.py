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
