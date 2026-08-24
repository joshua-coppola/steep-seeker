import pytest

from core.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_index_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Steep Seeker" in response.data
