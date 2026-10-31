"""Optional walking to a neighbouring district, and grid size."""

import pytest

import run_experiments
from agents import ASSIGNED, COMPLETED, WAITING
from helpers import assert_reproduces_stored, legacy_model, make_model, run
from routing import congestion_factor


def test_walk_off_and_grid_30_reproduce_results(tmp_path):
    """Explicit raw columns walk_radius 0 (no "walking" column) and a 30x30
    grid reproduce the stored S1-S4 values (seeds 1-2)."""
    def explicit_off(configs):
        configs = configs.drop(columns="walking")
        configs["walk_radius"] = 0
        configs["walk_minutes_per_district"] = 3
        configs["width"] = configs["height"] = 30
        return configs

    assert_reproduces_stored(tmp_path, edit=explicit_off, seeds=[1, 2])


def two_riders(walk_radius):
    # Rider 1 boards at (0, 0) and rides along y = 0 to (10, 0). Rider 2
    # requests at minute 1 at (5, 1), one district off that route.
    return make_model([(0, 0)], [(0, (0, 0), (10, 0)), (1, (5, 1), (8, 0))],
                      duration=30, capacity=2, sharing_mode="no_detour",
                      walk_radius=walk_radius)


def test_no_detour_accepts_passenger_who_walks_onto_route():
    refused = two_riders(walk_radius=0)
    refused.step()
    refused.step()
    assert refused.passengers[1].status == WAITING

    m = two_riders(walk_radius=1)
    m.step()
    m.step()
    p = m.passengers[1]
    assert p.status == ASSIGNED
    assert p.pickup_district == (5, 0)
    assert p.promised_pickup == 5  # taxi at (1, 0) at minute 1, 4 districts
    run(m)  # invariants: the walker is in the district when boarding
    assert p.status == COMPLETED
    assert p.pickup_time == 5
    assert p.walk_minutes == 3
    assert p.waiting_time == 4  # includes the walk
    assert p.individual_time == 3  # from the pickup district (5, 0) to (8, 0)
    assert p.extra_delay == 0
    assert p.shared
    assert m.latest_metrics["walked_pct"] == 50
    assert m.latest_metrics["avg_walk_minutes"] == 1.5


def test_walking_pickup_never_makes_taxi_wait():
    # The taxi at (5, 0) reaches the neighbour (5, 1) in 1 minute, before a
    # 3-minute walker could, so it proposes the origin (5, 2) at minute 2.
    m = make_model([(5, 0)], [(0, (5, 2), (5, 8))], duration=30, walk_radius=1)
    m.step()
    p = m.passengers[0]
    assert (p.pickup_district, p.promised_pickup) == ((5, 2), 2)
    # A walker needing only 1 minute is there in time: pickup at (5, 1) at 1.
    m = make_model([(5, 0)], [(0, (5, 2), (5, 8))], duration=30, walk_radius=1,
                   walk_minutes_per_district=1)
    m.step()
    p = m.passengers[0]
    assert (p.pickup_district, p.promised_pickup) == ((5, 1), 1)
    run(m)
    assert p.pickup_time == 1 and p.extra_delay == 0


def test_tie_prefers_no_walking():
    # The taxi is already at the origin: pickup at minute 0 there; no
    # neighbour can be earlier, so the passenger does not walk.
    m = run(make_model([(3, 3)], [(0, (3, 3), (6, 3))], duration=20, walk_radius=1,
                       walk_minutes_per_district=1))
    assert m.passengers[0].pickup_district == (3, 3)
    assert m.latest_metrics["walked_pct"] == 0


@pytest.mark.parametrize("mode,capacity", [("none", 1), ("no_detour", 2),
                                           ("detour", 2), ("detour", 4)])
@pytest.mark.parametrize("congestion", ["off", "center"])
def test_invariants_with_walking(mode, capacity, congestion):
    # helpers.run checks after every step: walkers are in the pickup district
    # when they board, promises and extra-delay limits hold.
    m = run(legacy_model(num_taxis=5, num_passengers=60, capacity=capacity,
                      sharing_mode=mode, arrival_mode="gradual", duration=90,
                      congestion=congestion, walk_radius=1, seed=2))
    r = m.latest_metrics
    assert r["walked_pct"] > 0
    assert r["max_extra_delay"] <= m.max_extra_delay
    for p in m.passengers:
        assert p.walk_minutes in (0, m.walk_minutes_per_district)
        if p.status == COMPLETED and p.pickup_district != p.origin:
            assert p.pickup_time - p.request_time >= p.walk_minutes


def test_invalid_walk_radius():
    with pytest.raises(ValueError):
        legacy_model(walk_radius=2)
    with pytest.raises(ValueError):
        legacy_model(walk_radius=1, walk_minutes_per_district=0)


@pytest.mark.parametrize("width,height", [(10, 10), (15, 12), (20, 20), (30, 30),
                                          (40, 40), (10, 40)])
def test_congestion_zones_at_any_grid_size(width, height):
    # Centre: one third of the grid in each direction; ring: 1 district around.
    factors = [congestion_factor((x, y), width, height, "center")
               for x in range(width) for y in range(height)]
    cx, cy = width // 3, height // 3
    assert factors.count(3) == cx * cy
    assert factors.count(2) == (cx + 2) * (cy + 2) - cx * cy  # ring fits
    m = run(legacy_model(width=width, height=height, num_passengers=30,
                      capacity=2, sharing_mode="detour", congestion="center",
                      walk_radius=1, duration=40))
    assert all(0 <= p.origin[0] < width and 0 <= p.origin[1] < height
               for p in m.passengers)


def test_optional_grid_and_walking_columns(tmp_path):
    config = tmp_path / "configs.csv"
    config.write_text(
        "config_id,description,num_taxis,num_passengers,capacity,sharing_mode,"
        "arrival_mode,arrival_window,duration,width,height,walk_radius\n"
        "A,small walk,3,20,1,none,all_at_start,30,30,12,30,1\n"
    )
    runs, passengers, _ = run_experiments.run(config, seeds=[1], out=tmp_path,
                                              charts=False)
    row = runs.iloc[0]
    assert (row["width"], row["height"], row["walk_radius"]) == (12, 30, 1)
    assert row["walk_minutes_per_district"] == 3  # default when absent
    xy = passengers["origin"].str.split(";", expand=True).astype(int)
    assert xy[0].max() < 12 and xy[1].max() < 30
