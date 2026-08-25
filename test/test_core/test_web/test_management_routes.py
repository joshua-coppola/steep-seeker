import shutil

import pytest

from core.datamodels.state import State
from core.osm import osm_processor
from core.support import mountain as mountain_module
from core.web import management_routes
from core.web.app import create_app
from core.web.management_app import create_management_app
from test.test_core.conftest import FakeElevation, FakeWeather


@pytest.fixture
def management_client(db_path):
    app = create_management_app(db_path=db_path)
    app.testing = True
    return app.test_client()


def test_public_app_does_not_expose_management_routes(db_path):
    app = create_app(db_path=db_path)
    app.testing = True
    client = app.test_client()

    response = client.get("/management-add-resort")

    assert response.status_code == 404


def test_management_app_serves_public_routes_too(management_client):
    response = management_client.get("/")

    assert response.status_code == 200
    assert b"Steep Seeker" in response.data


def test_management_nav_link_appears_on_every_page_in_management_app(
    management_client,
):
    response = management_client.get("/")

    body = response.data.decode()
    assert 'href="/management-add-resort"' in body


def test_management_nav_link_absent_from_public_app(db_path):
    app = create_app(db_path=db_path)
    app.testing = True
    client = app.test_client()

    response = client.get("/")

    body = response.data.decode()
    assert 'href="/management-add-resort"' not in body


def test_management_add_resort_lists_available_osm_files(
    management_client, tmp_path, monkeypatch
):
    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    (osm_dir / "UT").mkdir(parents=True)
    (osm_dir / "VT" / "Test1.osm").write_text("")
    (osm_dir / "UT" / "Test2.osm").write_text("")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    response = management_client.get("/management-add-resort")

    assert response.status_code == 200
    body = response.data.decode()
    assert "VT/Test1" in body
    assert "UT/Test2" in body


def test_management_add_resort_excludes_mountains_already_in_db(
    management_client, db_path, mountain_factory, tmp_path, monkeypatch
):
    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    (osm_dir / "UT").mkdir(parents=True)
    (osm_dir / "VT" / "Test1.osm").write_text("")
    (osm_dir / "UT" / "Test2.osm").write_text("")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    mountain_factory(mountain_id="1", name="Test1", state=State.VERMONT).to_db(db_path)

    response = management_client.get("/management-add-resort")

    body = response.data.decode()
    assert "VT/Test1" not in body
    assert "UT/Test2" in body


def test_management_add_resort_ingests_selected_file_and_redirects(
    management_client, db_path, tmp_path, monkeypatch
):
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)
    monkeypatch.setattr(mountain_module, "Weather", FakeWeather)
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    shutil.copy("test/test_core/test_osm/test.osm", osm_dir / "VT" / "test.osm")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    response = management_client.post("/management-add-resort", data={"q": "VT/test"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/interactive-map/VT/test"

    # follow the redirect against the same seeded db
    follow = management_client.get(response.headers["Location"])
    assert follow.status_code == 200
    assert b"test" in follow.data
