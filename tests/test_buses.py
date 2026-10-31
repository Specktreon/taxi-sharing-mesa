"""Optional buses: lines, mode choice, bus journeys and capacity."""

import pandas as pd
import pytest

from agents import BUS, COMPLETED, TAXI
from buses import choose_bus_trip, make_bus_lines
from config import BUS_CAPACITY, BUS_MIN_TRIP, BUSES_PER_LINE
from helpers import (assert_reproduces_stored, check_invariants, legacy_model,
                     make_model, run)
GRID = {"width": 20, "height": 20}


def test_lines_and_stops():
    lines = make_bus_lines(20, 20)
    assert [line.name for line in lines] == ["H1", "H2", "H3", "V1", "V2", "V3"]
    assert [line.cells[0] for line in lines[:3]] == [(0, 5), (0, 10), (0, 15)]
    assert [line.cells[0] for line in lines[3:]] == [(5, 0), (10, 0), (15, 0)]
    xs = sorted(x for x, _ in lines[0].stop_index)
    assert xs == [0, 3, 6, 9, 12, 15, 18, 19]  # every 3, both ends
    thirty = make_bus_lines(30, 30)
    assert [line.cells[0][1] for line in thirty[:3]] == [7, 15, 22]
    assert [line.cells[0][0] for line in thirty[3:]] == [7, 15, 22]
    m = legacy_model(buses=True, **GRID)
    assert BUSES_PER_LINE == 2 and len(m.buses) == 12  # same fleet as 4 x 3
    assert all(b.capacity == BUS_CAPACITY for b in m.buses)


def test_mode_choice_least_walking():
    lines = make_bus_lines(20, 20)
    line, board, alight = choose_bus_trip(lines, (0, 6), (19, 4))
    assert (line.name, board, alight) == ("H1", (0, 5), (19, 5))
    # Origin (0, 0) is 5 districts from the nearest stops (0, 5) and (5, 0).
    assert choose_bus_trip(lines, (0, 0), (19, 4)) is None
    # Within BUS_WALK_MAX = 3 of a stop at both ends, and exactly 3 away.
    assert choose_bus_trip(lines, (0, 8), (19, 8)) is not None
    assert choose_bus_trip(lines, (0, 8), (19, 1)) is None  # (19, 1): 4 from H1


def test_short_trips_never_take_the_bus():
    lines = make_bus_lines(20, 20)
    assert BUS_MIN_TRIP == 6
    # Stops (0, 5) and (3, 5) / (6, 5) are near both ends, but the trip is short.
    assert choose_bus_trip(lines, (0, 6), (4, 5)) is None  # 5 districts
    line, board, alight = choose_bus_trip(lines, (0, 6), (5, 5))  # 6 districts
    assert (line.name, board, alight) == ("H1", (0, 5), (6, 5))


def test_passenger_near_both_ends_rides_the_bus():
    # H1 runs along y = 5. The passenger walks 1 district (3 min) to (0, 5).
    # H1's second bus starts at x = 19 heading west, reaches (0, 5) at minute
    # 19, turns, boards the passenger, stands 1 min, drives 19 districts to
    # (19, 5) (minute 39), stands 1 min for alighting (40), then the
    # passenger walks 1 district to (19, 4): arrival 43.
    m = make_model([(10, 10)], [(0, (0, 6), (19, 4))], buses=True,
                   boarding_minutes=1, **GRID)
    p = m.passengers[0]
    assert p.mode == BUS and p.patience is None
    run(m)
    assert p.status == COMPLETED
    assert (p.pickup_time, p.alight_time, p.arrival_time) == (19, 40, 43)
    assert (p.waiting_time, p.in_vehicle_time, p.total_time) == (19, 21, 43)
    assert p.walk_minutes == 6
    assert p.extra_delay is None
    assert sum(m.message_counts.values()) == 0  # never contacts taxis
    r = m.latest_metrics
    assert r["bus_share_pct"] == 100
    assert r["completed_pct_bus"] == 100
    assert r["avg_total_completed_bus"] == 43
    assert pd.isna(r["completed_pct_taxi"])
    assert r["total_distance"] == 0  # the taxi never moved
    assert r["bus_distance"] > 0
    assert r["avg_bus_occupancy"] > 0


def test_passenger_far_from_stops_takes_a_taxi():
    m = run(make_model([(1, 1)], [(0, (0, 0), (19, 4))], buses=True, **GRID))
    p = m.passengers[0]
    assert p.mode == TAXI and p.status == COMPLETED
    assert m.latest_metrics["bus_share_pct"] == 0
    assert m.latest_metrics["completed_pct_taxi"] == 100


def test_bus_never_exceeds_capacity():
    # 25 passengers queue at the same stop, all going the same way.
    requests = [(0, (0, 6), (19, 4))] * 25
    m = make_model([(10, 10)], requests, buses=True, boarding_minutes=1,
                   duration=120, **GRID)
    most = 0
    while m.running:
        m.step()
        check_invariants(m)
        most = max(most, max(len(b.onboard) for b in m.buses))
    assert most == BUS_CAPACITY
    assert m.latest_metrics["completed"] == 25


@pytest.mark.parametrize("mode,capacity", [("none", 1), ("no_detour", 2),
                                           ("detour", 2), ("detour", 4)])
def test_invariants_with_buses_and_all_features(mode, capacity):
    m = run(legacy_model(num_taxis=6, num_passengers=100, capacity=capacity,
                      sharing_mode=mode, arrival_mode="gradual", duration=120,
                      arrival_window=90, buses=True, walk_radius=1,
                      congestion="center", patience_min=10, patience_max=30,
                      seed=3, **GRID))
    r = m.latest_metrics
    assert 0 < r["bus_share_pct"] < 100
    assert r["completed_pct_bus"] > 0 and r["completed_pct_taxi"] > 0
    assert r["max_extra_delay"] <= m.max_extra_delay
    assert all(p.status != "abandoned" for p in m.passengers if p.mode == BUS)


def test_all_features_off_explicitly_reproduces_results(tmp_path):
    """Every feature switched off with explicit raw model columns (buses,
    walk_radius, congestion, patience_max) reproduces the stored S1-S4 values
    (seeds 1-2)."""
    def explicit_off(configs):
        configs = configs.drop(columns=["walking", "patience"])
        configs["buses"] = False
        configs["walk_radius"] = 0
        configs["congestion"] = "off"
        configs["patience_max"] = None
        return configs

    assert_reproduces_stored(tmp_path, edit=explicit_off, seeds=[1, 2])
