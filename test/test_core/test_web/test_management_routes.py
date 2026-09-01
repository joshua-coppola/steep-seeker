import shutil

import pytest
from shapely import LineString

from core.datamodels.season_pass import Season_Pass
from core.datamodels.state import State
from core.osm import osm_processor
from core.support import mountain as mountain_module
from core.support.blacklist import add_to_blacklist, is_blacklisted
from core.support.mountain import Mountain
from core.support.utils import get_mountain_rating
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
    assert response.headers["Location"] == "/management-edit-resort?q=test,+VT"

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


def test_management_edit_resort_rotates_clockwise(
    management_client, db_path, mountain_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    mountain_factory(
        mountain_id="1", name="Bolton Valley", state=State.VERMONT, direction="n"
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "rotate": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.direction == "e"


def test_management_edit_resort_rotates_counterclockwise(
    management_client, db_path, mountain_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    mountain_factory(
        mountain_id="1", name="Bolton Valley", state=State.VERMONT, direction="n"
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "rotate_ccw": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.direction == "w"


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


def test_management_edit_resort_delete_trail_recalculates_mountain_stats(
    management_client, db_path, mountain_factory, trail_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    keep = trail_factory(
        trail_id="w1",
        mountain_id="1",
        name="Easy",
        geometry=LineString([[0, 0, 0], [1, 1, 100]]),
        length=200,
        difficulty=20.0,
    )
    drop = trail_factory(
        trail_id="w2",
        mountain_id="1",
        name="Hard",
        geometry=LineString([[0, 0, 0], [1, 1, 500]]),
        length=200,
        difficulty=40.0,
    )
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        difficulty=30.0,
        beginner_friendliness=30.0,
        vertical=500,
        trails={"w1": keep, "w2": drop},
    ).to_db(db_path)

    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete": "w2"},
    )

    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.difficulty == 20.0
    assert mountain.beginner_friendliness == 20.0
    assert mountain.vertical == 100


def test_management_edit_resort_trail_difficulty_edit_recalculates_mountain_stats(
    management_client, db_path, mountain_factory, trail_factory, monkeypatch
):
    monkeypatch.setattr(management_routes, "create_map", lambda *a, **k: None)
    monkeypatch.setattr(management_routes, "create_thumbnail", lambda *a, **k: None)

    trail = trail_factory(
        trail_id="w42",
        mountain_id="1",
        name="Test Trail",
        length=200,
        difficulty=25.0,
        steepest_30m=20.0,
        gladed=False,
        ungroomed=False,
    )
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        difficulty=25.0,
        beginner_friendliness=25.0,
        trails={"w42": trail},
    ).to_db(db_path)

    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "trail_id": "w42", "gladed": "True"},
    )

    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    # trail difficulty 25.0 -> 30.5 (gladed bonus), and it's the only rated
    # trail, so the mountain rating follows it
    assert mountain.trails["w42"].difficulty == 30.5
    assert mountain.difficulty == 30.5
    assert mountain.beginner_friendliness == 30.5


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


def test_management_edit_resort_delete_resort_requires_exact_confirmation(
    management_client, db_path, mountain_factory
):
    mountain_factory(mountain_id="1", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete_resort": "delete"},
    )

    assert response.status_code == 200
    assert Mountain.from_name("Bolton Valley", State.VERMONT, db_path) is not None


def test_management_edit_resort_deletes_resort(
    management_client, db_path, mountain_factory, trail_factory, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    osm_path = osm_dir / "VT" / "Bolton Valley.osm"
    osm_path.write_text("")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    maps_dir = tmp_path / "static" / "maps" / "VT"
    maps_dir.mkdir(parents=True)
    (maps_dir / "Bolton Valley.svg").write_text("")
    thumbnails_dir = tmp_path / "static" / "thumbnails" / "VT"
    thumbnails_dir.mkdir(parents=True)
    (thumbnails_dir / "Bolton Valley.svg").write_text("")

    trail = trail_factory(trail_id="w42", mountain_id="1")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"w42": trail},
    ).to_db(db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "delete_resort": "DELETE"},
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Select a resort above to view it." in body

    assert Mountain.from_name("Bolton Valley", State.VERMONT, db_path) is None
    assert not (maps_dir / "Bolton Valley.svg").exists()
    assert not (thumbnails_dir / "Bolton Valley.svg").exists()
    # osm file is kept by default
    assert osm_path.exists()


def test_management_edit_resort_deletes_resort_and_osm_file_when_checked(
    management_client, db_path, mountain_factory, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    osm_path = osm_dir / "VT" / "Bolton Valley.osm"
    osm_path.write_text("")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    mountain_factory(mountain_id="1", name="Bolton Valley", state=State.VERMONT).to_db(
        db_path
    )

    response = management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "delete_resort": "DELETE",
            "delete_osm": "True",
        },
    )

    assert response.status_code == 200
    assert Mountain.from_name("Bolton Valley", State.VERMONT, db_path) is None
    assert not osm_path.exists()


@pytest.fixture
def refresh_setup(
    db_path, mountain_factory, trail_factory, osm_file, tmp_path, monkeypatch
):
    """
    Common setup for refresh tests: a mountain named to match the OSM
    fixture file (159 trails / 20 lifts, mountain_id preserved via
    explicit override), the fixture file copied into a sandboxed OSM_DIR,
    real Elevation/Weather calls faked out, and create_map/create_thumbnail
    replaced with call-count spies.
    """
    monkeypatch.setattr(osm_processor, "Elevation", FakeElevation)
    monkeypatch.setattr(mountain_module, "Weather", FakeWeather)

    calls = {"create_map": 0, "create_thumbnail": 0}
    monkeypatch.setattr(
        management_routes,
        "create_map",
        lambda *a, **k: calls.__setitem__("create_map", calls["create_map"] + 1),
    )
    monkeypatch.setattr(
        management_routes,
        "create_thumbnail",
        lambda *a, **k: calls.__setitem__(
            "create_thumbnail", calls["create_thumbnail"] + 1
        ),
    )

    osm_dir = tmp_path / "osm"
    (osm_dir / "VT").mkdir(parents=True)
    shutil.copy(osm_file, osm_dir / "VT" / "Bolton Valley.osm")
    monkeypatch.setattr(management_routes, "OSM_DIR", str(osm_dir))

    osm_old_dir = tmp_path / "osm-old"
    monkeypatch.setattr(management_routes, "OSM_OLD_DIR", str(osm_old_dir))

    old_trail = trail_factory(trail_id="old-trail", mountain_id="1")
    mountain_factory(
        mountain_id="1",
        name="Bolton Valley",
        state=State.VERMONT,
        trails={"old-trail": old_trail},
        lifts={},
    ).to_db(db_path)

    return {"osm_dir": osm_dir, "osm_old_dir": osm_old_dir, "calls": calls}


def test_management_edit_resort_stats_refresh_rebuilds_trails_and_lifts(
    management_client, db_path, refresh_setup
):
    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "stats_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.mountain_id == "1"
    assert "old-trail" not in mountain.trails
    assert len(mountain.trails) == 159
    assert len(mountain.lifts) == 20
    assert refresh_setup["calls"]["create_map"] == 1
    assert refresh_setup["calls"]["create_thumbnail"] == 1


def test_management_edit_resort_stats_refresh_respects_blacklist(
    management_client, db_path, refresh_setup
):
    add_to_blacklist("1", "w11", db_path)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "stats_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "w11" not in mountain.trails
    assert "w10" in mountain.trails


def test_management_edit_resort_stats_refresh_ignore_areas(
    management_client, db_path, refresh_setup
):
    response = management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "stats_refresh": "True",
            "ignore_areas": "True",
        },
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    # w10 is an area trail, w11 is a line trail
    assert "w10" not in mountain.trails
    assert "w11" in mountain.trails


def test_management_edit_resort_stats_refresh_rates_off_kept_trails_only(
    management_client, db_path, refresh_setup
):
    # A plain refresh rates the mountain off all 159 parsed trails.
    management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "stats_refresh": "True"},
    )
    full = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)

    # Refreshing again with ignore_areas drops the area trails; the persisted
    # rating must reflect only what was actually saved, not the full parse.
    management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "stats_refresh": "True",
            "ignore_areas": "True",
        },
    )
    no_areas = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)

    assert not any(t.area for t in no_areas.trails.values())
    assert len(no_areas.trails) < len(full.trails)
    recomputed = get_mountain_rating(
        [
            t.difficulty
            for t in no_areas.trails.values()
            if t.length > 100 and t.difficulty is not None
        ]
    )
    assert (no_areas.difficulty, no_areas.beginner_friendliness) == recomputed
    assert (no_areas.difficulty, no_areas.beginner_friendliness) != (
        full.difficulty,
        full.beginner_friendliness,
    )


def test_management_edit_resort_stats_refresh_missing_file_is_a_no_op(
    management_client, db_path, refresh_setup
):
    (refresh_setup["osm_dir"] / "VT" / "Bolton Valley.osm").unlink()

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "stats_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "old-trail" in mountain.trails
    # a failed refresh leaves the existing map alone
    assert refresh_setup["calls"]["create_map"] == 0


def test_management_edit_resort_map_refresh_only_regenerates_map(
    management_client, db_path, refresh_setup
):
    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "map_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "old-trail" in mountain.trails
    assert refresh_setup["calls"]["create_map"] == 1
    assert refresh_setup["calls"]["create_thumbnail"] == 1


def test_management_edit_resort_full_refresh_fetches_and_rebuilds(
    management_client, db_path, refresh_setup, osm_file, monkeypatch
):
    fetched_bboxes = []
    with open(osm_file, "rb") as f:
        fixture_bytes = f.read()

    class FakeOSM:
        def get(self, bounding_box):
            fetched_bboxes.append(bounding_box)
            return fixture_bytes

    monkeypatch.setattr(management_routes, "OSM", FakeOSM)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "full_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert mountain.mountain_id == "1"
    assert len(mountain.trails) == 159
    assert len(mountain.lifts) == 20
    assert len(fetched_bboxes) == 1
    assert (
        refresh_setup["osm_dir"] / "VT" / "Bolton Valley.osm"
    ).read_bytes() == fixture_bytes
    assert refresh_setup["calls"]["create_map"] == 1


def test_management_edit_resort_full_refresh_ignore_areas(
    management_client, db_path, refresh_setup, osm_file, monkeypatch
):
    class FakeOSM:
        def get(self, bounding_box):
            with open(osm_file, "rb") as f:
                return f.read()

    monkeypatch.setattr(management_routes, "OSM", FakeOSM)

    response = management_client.get(
        "/management-edit-resort",
        query_string={
            "q": "Bolton Valley, VT",
            "full_refresh": "True",
            "ignore_areas": "True",
        },
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    # w10 is an area trail, w11 is a line trail
    assert "w10" not in mountain.trails
    assert "w11" in mountain.trails


def test_management_edit_resort_full_refresh_archives_old_osm_file(
    management_client, db_path, refresh_setup, osm_file, monkeypatch
):
    old_bytes = (refresh_setup["osm_dir"] / "VT" / "Bolton Valley.osm").read_bytes()

    class FakeOSM:
        def get(self, bounding_box):
            with open(osm_file, "rb") as f:
                return f.read()

    monkeypatch.setattr(management_routes, "OSM", FakeOSM)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "full_refresh": "True"},
    )

    assert response.status_code == 200
    archived = list((refresh_setup["osm_old_dir"] / "VT").glob("* Bolton Valley.osm"))
    assert len(archived) == 1
    assert archived[0].read_bytes() == old_bytes


def test_management_edit_resort_full_refresh_no_existing_file_skips_archiving(
    management_client, db_path, refresh_setup, osm_file, monkeypatch
):
    (refresh_setup["osm_dir"] / "VT" / "Bolton Valley.osm").unlink()

    class FakeOSM:
        def get(self, bounding_box):
            with open(osm_file, "rb") as f:
                return f.read()

    monkeypatch.setattr(management_routes, "OSM", FakeOSM)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "full_refresh": "True"},
    )

    assert response.status_code == 200
    assert not refresh_setup["osm_old_dir"].exists()
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert len(mountain.trails) == 159


def test_management_edit_resort_full_refresh_failed_fetch_leaves_mountain_unchanged(
    management_client, db_path, refresh_setup, monkeypatch
):
    class FakeOSM:
        def get(self, bounding_box):
            return None

    monkeypatch.setattr(management_routes, "OSM", FakeOSM)

    response = management_client.get(
        "/management-edit-resort",
        query_string={"q": "Bolton Valley, VT", "full_refresh": "True"},
    )

    assert response.status_code == 200
    mountain = Mountain.from_name("Bolton Valley", State.VERMONT, db_path)
    assert "old-trail" in mountain.trails
    # a failed fetch leaves the existing map alone
    assert refresh_setup["calls"]["create_map"] == 0
