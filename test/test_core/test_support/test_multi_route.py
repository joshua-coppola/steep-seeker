import pytest

from core.support.multi_route import get_multi_route


def test_get_multi_route_picks_the_gentler_branch():
    # a simple fork: top splits into a steep left line and a gentler right
    # line, both rejoining at the same bottom point
    top = (-111.6, 40.6, 100.0)
    mid_left = (-111.601, 40.599, 60.0)  # steep -- drops 40m
    mid_right = (-111.599, 40.599, 80.0)  # gentle -- drops 20m
    bottom = (-111.6, 40.598, 40.0)

    branch_left = [top, mid_left, bottom]
    branch_right = [top, mid_right, bottom]

    route = get_multi_route([branch_left, branch_right])

    assert route["type"] == "LineString"
    assert route["coordinates"][0] == list(top)
    assert route["coordinates"][-1] == list(bottom)
    elevations = [point[2] for point in route["coordinates"]]
    assert 80.0 in elevations
    assert 60.0 not in elevations


def test_get_multi_route_rejoin_uses_only_the_necessary_branches():
    # a shared trunk above and below a fork -- the route should keep both
    # trunk segments and pick only the gentler of the two middle branches
    top = (-111.6, 40.60, 100.0)
    junction_top = (-111.6, 40.599, 90.0)
    mid_left = (-111.601, 40.598, 50.0)  # steep
    mid_right = (-111.599, 40.598, 70.0)  # gentle
    junction_bottom = (-111.6, 40.597, 40.0)
    bottom = (-111.6, 40.596, 30.0)

    branch_top = [top, junction_top]
    branch_left = [junction_top, mid_left, junction_bottom]
    branch_right = [junction_top, mid_right, junction_bottom]
    branch_bottom = [junction_bottom, bottom]

    route = get_multi_route([branch_top, branch_left, branch_right, branch_bottom])

    elevations = [point[2] for point in route["coordinates"]]
    # both trunk segments are kept (only path from top to bottom)
    assert 100.0 in elevations
    assert 90.0 in elevations
    assert 40.0 in elevations
    assert 30.0 in elevations
    # the gentler middle branch is used, not the steeper one
    assert 70.0 in elevations
    assert 50.0 not in elevations


def test_get_multi_route_always_starts_and_ends_at_the_true_top_and_bottom():
    # a short access stub from the true top down to a near-top point, then
    # a long gentle line to the bottom. Unlike an area trail's banded
    # start/end candidates (any point within a fraction of the vertical
    # drop), a multi-route trail must always start/end at its actual
    # highest/lowest point -- not skip the stub just because a nearby
    # point would make for a shorter/gentler route
    top = (-111.6, 40.60, 100.0)
    near_top = (-111.6, 40.599, 96.0)
    mid = (-111.6, 40.598, 50.0)
    bottom = (-111.6, 40.597, 0.0)

    branch_stub = [top, near_top]
    branch_main = [near_top, mid, bottom]

    route = get_multi_route([branch_stub, branch_main])

    assert route["coordinates"][0] == list(top)
    assert route["coordinates"][-1] == list(bottom)


def test_get_multi_route_continues_past_a_local_elevation_dip_to_its_real_end():
    # the trail passes through a low point partway down (e.g. where it
    # crosses another, unrelated trail) that happens to be the elevation
    # minimum along the way, then continues to its real, topological end
    # a bit further on (a flat runout or slight uphill kick before it
    # actually stops). Pinning to the elevation extreme alone would wrongly
    # stop the route at the crossing; the real endpoint is a dead end
    # (degree-1) and the crossing point is just an ordinary pass-through
    # (degree-2), so degree -- not elevation -- must decide this
    top = (-111.6, 40.60, 100.0)
    crossing = (-111.6, 40.599, 20.0)  # elevation minimum, but not a dead end
    real_end = (-111.6, 40.598, 25.0)  # true dead end, slightly higher

    branch = [top, crossing, real_end]

    route = get_multi_route([branch])

    assert route["coordinates"][0] == list(top)
    assert route["coordinates"][-1] == list(real_end)


def test_get_multi_route_handles_a_single_dead_end_spur_into_a_loop():
    # a "lollipop": one real dead-end spur feeding into an otherwise
    # unbroken loop (every other node has degree 2, the spur tip has
    # degree 1). Restricting candidates to dead ends only works when
    # there are at least two of them -- with only one, that single node
    # would become both the start and end candidate, collapsing the route
    # to zero real points and crashing the LineString construction
    top = (-111.6, 40.60, 100.0)
    junction = (-111.6, 40.599, 80.0)
    loop_a = (-111.601, 40.598, 60.0)
    loop_b = (-111.599, 40.598, 60.0)

    branch_spur = [top, junction]
    branch_loop = [junction, loop_a, loop_b, junction]

    route = get_multi_route([branch_spur, branch_loop])

    assert route["coordinates"][0] == list(top)
    assert len(route["coordinates"]) >= 2


def test_get_multi_route_starts_at_the_highest_point_even_at_a_forked_top():
    # Real-world case (Big Sky, MT's "Rips"): the run's top is a fork where
    # two branches diverge from one shared point -- that point is never a
    # mapped dead end (degree 2, not 1), and the network's only two real
    # dead ends are elsewhere: a lower-elevation mid-network spur tip and
    # the true bottom. Restricting the start to dead ends only (like the
    # end) would wrongly start the route at that spur tip instead of the
    # true, higher-up top.
    top = (-111.6, 40.60, 100.0)
    mid_a = (-111.601, 40.599, 85.0)
    junction = (-111.6, 40.598, 60.0)
    spur_tip = (-111.599, 40.597, 70.0)
    bottom = (-111.6, 40.596, 0.0)

    branch_a = [top, mid_a, junction]
    branch_b = [top, junction]
    branch_spur = [junction, spur_tip]
    branch_bottom = [junction, bottom]

    route = get_multi_route([branch_a, branch_b, branch_spur, branch_bottom])

    assert route["coordinates"][0] == list(top)
    assert route["coordinates"][-1] == list(bottom)


def test_get_multi_route_raises_when_branches_are_disconnected():
    branch_a = [(-111.6, 40.6, 100.0), (-111.6, 40.599, 90.0)]
    # far enough away to share no coordinate with branch_a
    branch_b = [(-110.0, 41.0, 200.0), (-110.0, 40.999, 190.0)]

    with pytest.raises(ValueError):
        get_multi_route([branch_a, branch_b])
