"""Optional buses: lines, mode choice, bus journeys and capacity."""

from pathlib import Path

import pandas as pd
import pytest

import run_experiments
from agents import BUS, COMPLETED, TAXI
from buses import choose_bus_trip, make_bus_lines
from config import BUS_CAPACITY, BUSES_PER_LINE
from helpers import check_invariants, make_model, run
from model import TaxiModel

ROOT = Path(__file__).resolve().parent.parent
GRID = {"width": 20, "height": 20}


def test_lines_and_stops():
    lines = make_bus_lines(20, 20)
    assert [line.name for line in lines] == ["H1", "H2", "V1", "V2"]
    assert lines[0].cells[0] == (0, 6) and lines[1].cells[0] == (0, 13)
    assert lines[2].cells[0] == (6, 0) and lines[3].cells[0] == (13, 0)
    xs = sorted(x for x, _ in lines[0].stop_index)
    assert xs == [0, 3, 6, 9, 12, 15, 18, 19]  # every 3, both ends
    thirty = make_bus_lines(30, 30)
    assert [thirty[0].cells[0][1], thirty[1].cells[0][1]] == [10, 20]
    assert [thirty[2].cells[0][0], thirty[3].cells[0][0]] == [10, 20]
    m = TaxiModel(buses=True, **GRID)
    assert len(m.buses) == 4 * BUSES_PER_LINE
    assert all(b.capacity == BUS_CAPACITY for b in m.buses)


def test_mode_choice_least_walking():
    lines = make_bus_lines(20, 20)
    line, board, alight = choose_bus_trip(lines, (0, 7), (19, 5))
    assert (line.name, board, alight) == ("H1", (0, 6), (19, 6))
    assert choose_bus_trip(lines, (0, 0), (3, 0)) is None  # far from all stops
    # Only stop (0, 6) is within 2 districts of both ends: no bus trip.
    assert choose_bus_trip(lines, (0, 7), (0, 5)) is None


def test_passenger_near_both_ends_rides_the_bus():
    # H1 runs along y = 6. The passenger walks 1 district (3 min) to (0, 6).
    # Bus 3 of H1 starts at x = 13 heading west, reaches (0, 6) at minute 13,
    # turns, boards the passenger, stands 1 min, drives 19 districts to
    # (19, 6) (minute 33), stands 1 min for alighting (34), then the
    # passenger walks 1 district to (19, 5): arrival 37.
    m = make_model([(10, 10)], [(0, (0, 7), (19, 5))], buses=True,
                   boarding_minutes=1, **GRID)
    p = m.passengers[0]
    assert p.mode == BUS and p.patience is None
    run(m)
    assert p.status == COMPLETED
    assert (p.pickup_time, p.alight_time, p.arrival_time) == (13, 34, 37)
    assert (p.waiting_time, p.in_vehicle_time, p.total_time) == (13, 21, 37)
    assert p.walk_minutes == 6
    assert p.extra_delay is None
    assert sum(m.message_counts.values()) == 0  # never contacts taxis
    r = m.latest_metrics
    assert r["bus_share_pct"] == 100
    assert r["completed_pct_bus"] == 100
    assert r["avg_total_completed_bus"] == 37
    assert pd.isna(r["completed_pct_taxi"])
    assert r["total_distance"] == 0  # the taxi never moved
    assert r["bus_distance"] > 0
    assert r["avg_bus_occupancy"] > 0


def test_passenger_far_from_stops_takes_a_taxi():
    m = run(make_model([(1, 1)], [(0, (0, 0), (3, 0))], buses=True, **GRID))
    p = m.passengers[0]
    assert p.mode == TAXI and p.status == COMPLETED
    assert m.latest_metrics["bus_share_pct"] == 0
    assert m.latest_metrics["completed_pct_taxi"] == 100


def test_bus_never_exceeds_capacity():
    # 25 passengers queue at the same stop, all going the same way.
    requests = [(0, (0, 7), (19, 5))] * 25
    m = make_model([(10, 10)], requests, buses=True, boarding_minutes=1,
                   duration=80, **GRID)
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
    m = run(TaxiModel(num_taxis=6, num_passengers=100, capacity=capacity,
                      sharing_mode=mode, arrival_mode="gradual", duration=120,
                      arrival_window=90, buses=True, walk_radius=1,
                      congestion="center", patience_min=10, patience_max=30,
                      seed=3, **GRID))
    r = m.latest_metrics
    assert 0 < r["bus_share_pct"] < 100
    assert r["completed_pct_bus"] > 0 and r["completed_pct_taxi"] > 0
    assert r["max_extra_delay"] <= m.max_extra_delay
    assert all(p.status != "abandoned" for p in m.passengers if p.mode == BUS)


def test_buses_off_reproduces_results(tmp_path):
    """An explicit buses = False column reproduces every stored value."""
    configs = pd.read_csv(ROOT / "experiments.csv")
    configs["buses"] = False
    config = tmp_path / "configs.csv"
    configs.to_csv(config, index=False)
    out = tmp_path / "out"
    run_experiments.run(config, out=out, charts=False)
    for name in ["runs.csv", "summary.csv", "passengers.csv"]:
        stored = pd.read_csv(ROOT / "results" / name)
        fresh = pd.read_csv(out / name)
        pd.testing.assert_frame_equal(fresh[stored.columns], stored,
                                      check_exact=True, obj=name)
