import shutil

import pytest

from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.osm import osm_processor
from core.support import mountain as mountain_module
from core.support.blacklist import is_blacklisted
from core.support.mountain import Mountain
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


def test_management_edit_resort_no_query_shows_selector_only(management_client):
    response = management_client.get("/management-edit-resort")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Select a resort above to view it." in body


def test_management_edit_resort_with_valid_mountain(
    management_client, db_path, mountain_factory
):
    mountain_factory(mountain_id="1", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    response = management_client.get(
        "/management-edit-resort", query_string={"q": "Bolton Valley, VT"}
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley, VT" in body
    assert "Trail Count" in body


def test_management_edit_resort_invalid_query_falls_back_to_selector(
    management_client, db_path, mountain_factory
):
    mountain_factory(mountain_id="1", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    response = management_client.get(
        "/management-edit-resort", query_string={"q": "Nonexistent, VT"}
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Select a resort above to view it." in body


def test_management_edit_resort_next_mountain_wraps_around(
    management_client, db_path, mountain_factory
):
    mountain_factory(mountain_id="1", name="Alta", state=State.UTAH).to_db(db_path)
    mountain_factory(mountain_id="2", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    # "Bolton Valley, VT" sorts after "Alta, UT" -- selecting the last
    # mountain alphabetically should wrap next_mountain back to the first
    response = management_client.get(
        "/management-edit-resort", query_string={"q": "Bolton Valley, VT"}
    )

    body = response.data.decode()
    assert 'value="Alta, UT"' in body


def test_management_edit_resort_updates_season_passes(
    management_client, db_path, mountain_factory
):

    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        season_passes=[Season_Pass.EPIC],
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "update_passes": "True",
            "ikon": "True",
            "indy": "True",
        },
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert set(mountain.season_passes) == {Season_Pass.IKON, Season_Pass.INDY}


def test_management_edit_resort_clears_season_passes_when_none_checked(
    management_client, db_path, mountain_factory
):

    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        season_passes=[Season_Pass.EPIC],
    ).to_db(db_path)

    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "update_passes": "True"},
    )

    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.season_passes == []


def test_management_edit_resort_updates_url(
    management_client, db_path, mountain_factory
):

    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        url="https://old.example.com",
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "url": "https://new.example.com"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.url == "https://new.example.com"


def test_management_edit_resort_renames_mountain_and_files(
    management_client, db_path, mountain_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)

    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    (osm_dir / "VT" / "Bolton Valley.osm").write_text("")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    # _rename_resort_files uses a hardcoded relative "static/thumbnails"
    # path, so give it a matching tree under a cwd sandboxed to tmp_path
    monkeypatch.chdir(tmp_path)
    thumbnails_dir = tmp_path / "static" / "thumbnails" / "VT"
    thumbnails_dir.mkdir(parents=True)
    (thumbnails_dir / "Bolton Valley.svg").write_text("")

    mountain_factory(mountain_id="1", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "rename": "Bolton Valley Resort"},
    )

    assert response.status_code == 200
    renamed = Mountain.from_name("Bolton Valley Resort", State.VERMONT, db_path)
    assert renamed is not None
    assert Mountain.from_name("Bolton Valley", State.VERMONT, db_path) is None

    assert (osm_dir / "VT" / "Bolton Valley Resort.osm").exists()
    assert not (osm_dir / "VT" / "Bolton Valley.osm").exists()
    assert (
        tmp_path / "static" / "thumbnails" / "VT" / "Bolton Valley Resort.svg"
    ).exists()


def test_management_edit_resort_updates_trail_gladed_and_recomputes_difficulty(
    management_client, db_path, mountain_factory, trail_factory
):
    trail = trail_factory(
        trail_id="w42",
        mountain_id="1",
        name="Test Trail",
        difficulty=25.0,
        steepest_30m=20.0,
        gladed=False,
        ungroomed=False,
    )
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "trail_id": "w42",
            "gladed": "True",
        },
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    updated_trail = mountain.trails["w42"]
    assert updated_trail.gladed is True
    assert updated_trail.ungroomed is False
    # weather_modifier recovered as 25.0 - 20.0 - 0 = 5.0, then
    # 20.0 + 5.0 + 5.5 (gladed bonus) = 30.5
    assert updated_trail.difficulty == 30.5


def test_management_edit_resort_unchecking_gladed_removes_bonus(
    management_client, db_path, mountain_factory, trail_factory
):
    trail = trail_factory(
        trail_id="w42",
        mountain_id="1",
        name="Test Trail",
        difficulty=30.5,
        steepest_30m=20.0,
        gladed=True,
        ungroomed=False,
    )
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    # gladed omitted entirely -- an unchecked checkbox isn't sent at all
    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "trail_id": "w42"},
    )

    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    updated_trail = mountain.trails["w42"]
    assert updated_trail.gladed is False
    assert updated_trail.difficulty == 25.0


def test_management_edit_resort_deletes_trail(
    management_client, db_path, mountain_factory, trail_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    trail = trail_factory(trail_id="w42", mountain_id="1", name="Test Trail")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete": "w42"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "w42" not in mountain.trails


def test_management_edit_resort_deletes_lift(
    management_client, db_path, mountain_factory, lift_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    lift = lift_factory(lift_id="w99", mountain_id="1", name="Test Lift")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        lifts={"w99": lift},
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete": "w99"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "w99" not in mountain.lifts


def test_management_edit_resort_deletes_and_blacklists(
    management_client, db_path, mountain_factory, trail_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    trail = trail_factory(trail_id="w42", mountain_id="1", name="Test Trail")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete": "w42", "blacklist": "True"},
    )

    assert is_blacklisted("1", "w42", db_path) is True


def test_management_edit_resort_delete_nonexistent_id_is_a_no_op(
    management_client, db_path, mountain_factory, trail_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    trail = trail_factory(trail_id="w42", mountain_id="1", name="Test Trail")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete": "nonexistent"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "w42" in mountain.trails
