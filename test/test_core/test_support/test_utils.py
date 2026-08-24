import shapely

from core.support.utils import (
    get_average_slope,
    get_length,
    get_max_slope,
    get_mountain_rating,
    get_steepest_pitch,
    get_trail_difficulty,
    get_vertical_drop,
    meters_to_feet,
    polygon_interior_grid,
    round_geometry_precision,
    space_line_points_evenly,
)


def test_meters_to_feet():
    assert meters_to_feet(1) == 3.28084


def test_meters_to_feet_none():
    assert meters_to_feet(None) is None


def test_round_geometry_precision_point():
    point = shapely.Point(-72.123456789012345, 43.987654321098765)

    rounded = round_geometry_precision(point)

    assert rounded == shapely.Point(-72.123457, 43.987654)


def test_round_geometry_precision_leaves_elevation_untouched():
    line = shapely.LineString(
        [(-72.1234567891, 43.1234567891, 1000.123456), (-72.2, 43.2, 1001.0)]
    )

    rounded = round_geometry_precision(line)

    assert list(rounded.coords) == [
        (-72.123457, 43.123457, 1000.123456),
        (-72.2, 43.2, 1001.0),
    ]


def test_space_line_points_evenly():
    test_line = shapely.LineString([[0, 0], [0.001, 0.001]])

    output_line = space_line_points_evenly(test_line)

    assert len(shapely.to_geojson(output_line)) == 1335


def test_polygon_interior_grid():
    test_polygon = shapely.Polygon([[0, 0], [0, 0.01], [0.02, 0.02], [0.01, 0]])

    output_points = polygon_interior_grid(test_polygon, spacing_feet=100)

    assert len(output_points.geoms) == 2651


def test_get_length():
    geojson = {
        "type": "LineString",
        "coordinates": [
            [-72.718289, 43.422299, 1500.0],
            [-72.718362, 43.422312, 1500.0],
        ],
    }

    assert round(get_length(geojson), 2) == 6.07


def test_get_vertical_drop_line():
    geometry = {
        "coordinates": [
            [-120.0, 40.0, 100],
            [-120.01, 40.01, 300],
            [-120.02, 40.02, 200],
        ]
    }
    assert get_vertical_drop(geometry) == 200


def test_get_vertical_drop_nested_area():
    geometry = {"coordinates": [[[-120.0, 40.0, 50], [-120.01, 40.01, 150]]]}
    assert get_vertical_drop(geometry) == 100


def test_get_vertical_drop_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_vertical_drop(geometry) is None


def test_get_max_slope():
    geometry = {
        "coordinates": [
            [-120.0, 40.0, 100],
            [-120.01, 40.01, 300],
            [-120.02, 40.02, 200],
        ]
    }
    assert round(get_max_slope(geometry), 2) == 8.13


def test_get_max_slope_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_max_slope(geometry) is None


def test_get_average_slope():
    geometry = {
        "coordinates": [
            [-120.0, 40.0, 100],
            [-120.01, 40.01, 300],
            [-120.02, 40.02, 200],
        ]
    }
    assert round(get_average_slope(geometry), 2) == 6.11


def test_get_average_slope_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_average_slope(geometry) is None


# A steady-grade line ~556m long, dropping 20m every ~55.6m (constant ~19.8 degree pitch)
STEADY_GRADE_LINE = {
    "coordinates": [[-120.0, 40.0 + i * 0.0005, 1000 - i * 20] for i in range(11)]
}


def test_get_steepest_pitch_finds_window():
    assert get_steepest_pitch(STEADY_GRADE_LINE, 100) == 19.8


def test_get_steepest_pitch_no_window_long_returns_none():
    # trail is ~556m; no 1000m window exists and 1000 > 30, so no fallback
    assert get_steepest_pitch(STEADY_GRADE_LINE, 1000) is None


def test_get_steepest_pitch_short_trail_falls_back_to_overall_slope():
    # trail is ~14m, shorter than the 30m window, so falls back to the
    # whole-trail slope instead of returning None
    geometry = {"coordinates": [[-120.0, 40.0, 100], [-120.0001, 40.0001, 105]]}
    assert get_steepest_pitch(geometry, 30) == 19.6


def test_get_steepest_pitch_no_elevations():
    geometry = {"coordinates": [[-120.0, 40.0, None], [-120.01, 40.01, None]]}
    assert get_steepest_pitch(geometry, 30) is None


def test_get_steepest_pitch_too_few_points():
    geometry = {"coordinates": [[-120.0, 40.0, 100]]}
    assert get_steepest_pitch(geometry, 30) is None


def test_get_trail_difficulty_plain():
    assert (
        get_trail_difficulty(20.0, gladed=False, ungroomed=False, weather_modifier=3.0)
        == 23.0
    )


def test_get_trail_difficulty_gladed_and_ungroomed_only_applies_gladed():
    # gladed and ungroomed don't stack; gladed wins
    assert (
        get_trail_difficulty(20.0, gladed=True, ungroomed=True, weather_modifier=3.0)
        == 28.5
    )


def test_get_trail_difficulty_gladed_only():
    assert (
        get_trail_difficulty(20.0, gladed=True, ungroomed=False, weather_modifier=0)
        == 25.5
    )


def test_get_trail_difficulty_ungroomed_only():
    assert (
        get_trail_difficulty(20.0, gladed=False, ungroomed=True, weather_modifier=0)
        == 22.5
    )


def test_get_trail_difficulty_no_steepest_30m_returns_none():
    assert (
        get_trail_difficulty(None, gladed=True, ungroomed=True, weather_modifier=3.0)
        is None
    )


def test_get_mountain_rating_no_trails_returns_none():
    assert get_mountain_rating([]) == (None, None)


def test_get_mountain_rating_single_trail_rates_both_the_same():
    # With nothing to compare against, the one trail defines both ends
    assert get_mountain_rating([15.0]) == (15.0, 15.0)


def test_get_mountain_rating_fewer_than_five_trails_rates_both_the_same():
    # Too few trails to distinguish a "top 5" from a "top 30", so
    # difficulty and beginner_friendliness end up identical
    assert get_mountain_rating([10, 20, 30]) == (20.0, 20.0)


def test_get_mountain_rating_weights_extremes_more_heavily():
    # difficulty leans on the hardest trails, beginner_friendliness on the
    # easiest - here that pulls them to opposite ends of the 1-10 range
    difficulty, beginner_friendliness = get_mountain_rating(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    )
    assert difficulty == 7.5
    assert beginner_friendliness == 3.5
