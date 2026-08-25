import pytest
from shapely import LineString, Point, Polygon

from core.datamodels.state import State
from core.web.app import create_app
from core.web.routes import _lift_feature, _sorted_trails_and_lifts, _trail_features


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


def test_privacy_policy_returns_ok(client):
    response = client.get("/privacy-policy")

    assert response.status_code == 200
    assert b"Privacy Policy" in response.data


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


def test_random_mountain_redirects_to_interactive_map(seeded_client):
    response = seeded_client.get("/random-mountain")

    assert response.status_code == 302
    valid_targets = {
        "/interactive-map/VT/Bolton%20Valley",
        "/interactive-map/VT/Killington",
        "/interactive-map/UT/Alta",
    }
    assert response.headers["Location"] in valid_targets


def test_sitemap_returns_xml(seeded_client):
    response = seeded_client.get("/sitemap.xml")

    assert response.status_code == 200
    assert response.mimetype == "text/xml"
    body = response.data.decode()
    assert "<urlset" in body
    assert "https://steepseeker.com/search" in body
    assert "https://steepseeker.com/explore-map" in body
    assert "https://steepseeker.com/trail-rankings" in body
    assert "https://steepseeker.com/lift-rankings" in body
    assert "https://steepseeker.com/map/VT/Bolton Valley" in body
    assert "https://steepseeker.com/interactive-map/UT/Alta" in body


def test_explore_map_returns_ok_with_all_mountains(seeded_client):
    response = seeded_client.get("/explore-map")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley" in body
    assert "Killington" in body
    assert "Alta" in body
    assert '"type": "FeatureCollection"' in body
    assert '"type": "Point"' in body


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


def test_search_invalid_state_returns_no_results(seeded_client):
    # an unparseable location should match nothing, not silently show
    # every mountain the way a missing/empty location does
    response = seeded_client.get("/search?location=Nonexistent")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley" not in body
    assert "Killington" not in body
    assert "Alta" not in body


def test_search_paginates(seeded_client):
    response = seeded_client.get("/search?limit=1&sort=name&order=asc")

    body = response.data.decode()
    assert "Alta" in body
    assert "Bolton Valley" not in body
    assert "Next Page" in body


def test_search_accepts_infinity_trailsmax(seeded_client):
    # search.js sends trailsmax=Infinity when its slider's upper handle is
    # maxed out, meaning "no limit"
    response = seeded_client.get("/search?trailsmax=Infinity")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley" in body
    assert "Killington" in body
    assert "Alta" in body


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


def test_rankings_invalid_state_returns_no_results(seeded_client):
    response = seeded_client.get("/rankings?state=Nonexistent")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Bolton Valley" not in body
    assert "Killington" not in body
    assert "Alta" not in body


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


def test_trail_rankings_invalid_state_returns_no_results(ranked_client):
    response = ranked_client.get("/trail-rankings?state=Nonexistent")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Trail A" not in body
    assert "Trail B" not in body


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


def test_lift_rankings_invalid_state_returns_no_results(ranked_client):
    response = ranked_client.get("/lift-rankings?state=Nonexistent")

    assert response.status_code == 200
    body = response.data.decode()
    assert "Lift A" not in body
    assert "Lift B" not in body


@pytest.fixture
def mapped_client(client, db_path, mountain_factory, trail_factory, lift_factory):
    line_trail = trail_factory(
        trail_id="line-1",
        mountain_id="1",
        name="Line Trail",
        area=False,
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 950]]),
        interior_geometry="",
        route=None,
        difficulty=25.0,
        steepest_30m=20.0,
    )
    area_trail = trail_factory(
        trail_id="area-1",
        mountain_id="1",
        name="Area Trail",
        area=True,
        geometry=Polygon(
            [[0, 0, 100], [0, 1, 100], [1, 1, 50], [1, 0, 50], [0, 0, 100]]
        ),
        interior_geometry=LineString([[0.4, 0.4, 80], [0.6, 0.6, 70]]),
        route=LineString([[0, 1, 100], [0.5, 0.5, 75], [1, 0, 50]]),
        difficulty=30.0,
        steepest_30m=25.0,
    )
    lift = lift_factory(
        lift_id="lift-1",
        mountain_id="1",
        name="Test Lift",
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 1100]]),
    )

    mountain_factory(
        mountain_id="1",
        name="TestMountain",
        state=State.VERMONT,
        direction="n",
        coordinates=Point(-72.0, 43.0),
        trails={"line-1": line_trail, "area-1": area_trail},
        lifts={"lift-1": lift},
    ).to_db(db_path)

    return client


def test_static_map_404_for_unknown_mountain(client):
    response = client.get("/map/VT/Nonexistent")

    assert response.status_code == 404


def test_static_map_404_for_invalid_state(client):
    response = client.get("/map/Nonexistent/Nonexistent")

    assert response.status_code == 404


def test_static_map_returns_ok(mapped_client):
    response = mapped_client.get("/map/VT/TestMountain")

    assert response.status_code == 200
    body = response.data.decode()
    assert "TestMountain" in body
    assert "Line Trail" in body
    assert "Area Trail" in body
    assert "Test Lift" in body
    assert "/maps/VT/TestMountain.svg" in body
    assert "/interactive-map/VT/TestMountain" in body


def test_interactive_map_404_for_unknown_mountain(client):
    response = client.get("/interactive-map/VT/Nonexistent")

    assert response.status_code == 404


def test_interactive_map_returns_ok(mapped_client):
    response = mapped_client.get("/interactive-map/VT/TestMountain")

    assert response.status_code == 200
    body = response.data.decode()
    assert "TestMountain" in body
    assert "Line Trail" in body
    assert "Area Trail" in body
    assert "Test Lift" in body


def test_interactive_map_geojson_includes_area_route_feature(mapped_client):
    response = mapped_client.get("/interactive-map/VT/TestMountain")

    body = response.data.decode()
    assert "isRoute" in body
    assert "routeCoordinates" in body


def test_sorted_trails_and_lifts_includes_unnamed_trails_and_lifts(
    mountain_factory, trail_factory, lift_factory
):
    named_trail = trail_factory(trail_id="w1", name="Named Trail", difficulty=10.0)
    unnamed_trail = trail_factory(trail_id="w2", name="", difficulty=20.0)
    named_lift = lift_factory(lift_id="l1", name="Named Lift")
    unnamed_lift = lift_factory(lift_id="l2", name="")

    mountain = mountain_factory(
        trails={"w1": named_trail, "w2": unnamed_trail},
        lifts={"l1": named_lift, "l2": unnamed_lift},
    )

    trails, lifts = _sorted_trails_and_lifts(mountain)

    # sorted by difficulty descending -- the unnamed trail rates higher
    assert [t.trail_id for t in trails] == ["w2", "w1"]
    assert {lift.lift_id for lift in lifts} == {"l1", "l2"}


def test_trail_features_line_trail_has_single_linestring_feature(trail_factory):

    line_trail = trail_factory(
        area=False,
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 950]]),
        interior_geometry="",
        route=None,
    )

    features = _trail_features(line_trail, direction="n", debug_mode=False)

    assert len(features) == 1
    assert features[0]["geometry"]["type"] == "LineString"
    assert "routeCoordinates" not in features[0]["properties"]


def test_trail_features_without_edit_query_has_no_tag_edit_form(trail_factory):
    line_trail = trail_factory(
        area=False,
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 950]]),
        interior_geometry="",
        route=None,
    )

    features = _trail_features(line_trail, direction="n", debug_mode=False)

    assert "update_tags" not in features[0]["properties"]["popupContent"]


def test_trail_features_with_edit_query_adds_tag_edit_form(trail_factory):
    line_trail = trail_factory(
        trail_id="w42",
        area=False,
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 950]]),
        interior_geometry="",
        route=None,
        gladed=True,
        ungroomed=False,
    )

    features = _trail_features(
        line_trail, direction="n", debug_mode=False, edit_query="TestMountain, VT"
    )

    popup = features[0]["properties"]["popupContent"]
    assert 'name="q" value="TestMountain, VT"' in popup
    assert 'name="trail_id" value="w42"' in popup
    assert 'id="gladed" name="gladed" value=True checked' in popup
    assert 'id="ungroomed" name="ungroomed" value=True checked' not in popup


def test_trail_features_with_edit_query_adds_delete_form(trail_factory):
    line_trail = trail_factory(
        trail_id="w42",
        area=False,
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 950]]),
        interior_geometry="",
        route=None,
    )

    features = _trail_features(
        line_trail, direction="n", debug_mode=False, edit_query="TestMountain, VT"
    )

    popup = features[0]["properties"]["popupContent"]
    assert 'id="delete_submit"' in popup
    assert 'name="delete" value="w42"' in popup
    assert 'id="blacklist"' in popup


def test_lift_feature_without_edit_query_has_no_delete_form(lift_factory):
    lift = lift_factory(
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 1100]])
    )

    feature = _lift_feature(lift, direction="n", weather_modifier=0, debug_mode=False)

    assert "delete_submit" not in feature["properties"]["popupContent"]


def test_lift_feature_with_edit_query_adds_delete_form(lift_factory):
    lift = lift_factory(
        lift_id="w99",
        geometry=LineString([[-72.0, 43.0, 1000], [-72.001, 43.001, 1100]]),
    )

    feature = _lift_feature(
        lift,
        direction="n",
        weather_modifier=0,
        debug_mode=False,
        edit_query="TestMountain, VT",
    )

    popup = feature["properties"]["popupContent"]
    assert 'name="delete" value="w99"' in popup
    assert 'id="blacklist"' in popup


def test_trail_features_area_trail_with_route_adds_route_feature(trail_factory):
    area_trail = trail_factory(
        area=True,
        geometry=Polygon(
            [[0, 0, 100], [0, 1, 100], [1, 1, 50], [1, 0, 50], [0, 0, 100]]
        ),
        interior_geometry=LineString([[0.4, 0.4, 80], [0.6, 0.6, 70]]),
        route=LineString([[0, 1, 100], [0.5, 0.5, 75], [1, 0, 50]]),
    )

    features = _trail_features(area_trail, direction="n", debug_mode=False)

    assert len(features) == 2
    polygon_feature, route_feature = features
    assert polygon_feature["geometry"]["type"] == "Polygon"
    assert "routeCoordinates" in polygon_feature["properties"]
    assert route_feature["geometry"]["type"] == "LineString"
    assert route_feature["properties"]["isRoute"] is True
    # the route line reuses the polygon's own difficulty color, shown
    # partially transparent (see interactive-map.js's style())
    assert (
        route_feature["properties"]["color"] == polygon_feature["properties"]["color"]
    )
    assert "popupContent" not in route_feature["properties"]

    # the name label moves from the polygon's border onto the route line,
    # which reads much better as a text path
    assert "label" not in polygon_feature["properties"]
    assert route_feature["properties"]["label"] == area_trail.name

    # name identifies the trail for the elevation-profile title regardless
    # of which feature was clicked, unlike label (on-map text only)
    assert polygon_feature["properties"]["name"] == area_trail.name


def test_trail_features_area_trail_without_route_has_single_feature(trail_factory):

    area_trail = trail_factory(
        area=True,
        geometry=Polygon(
            [[0, 0, 100], [0, 1, 100], [1, 1, 50], [1, 0, 50], [0, 0, 100]]
        ),
        interior_geometry=LineString([[0.4, 0.4, 80], [0.6, 0.6, 70]]),
        route=None,
    )

    features = _trail_features(area_trail, direction="n", debug_mode=False)

    assert len(features) == 1
    assert "routeCoordinates" not in features[0]["properties"]
