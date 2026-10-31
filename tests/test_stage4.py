"""General insertion (stages 3-4), capacity up to 4, boarding time, distances."""

import json
import math
from pathlib import Path

import pytest

from agents import DROPOFF, PICKING_UP, PICKUP
from helpers import legacy_model, make_model, run, stops_of


def test_insertion_while_driving_to_first_pickup():
    # Taxi at (0,0) drives to P1 at (5,0). At minute 1 P2 asks for (3,1)->(7,1),
    # which is not on the planned route: only the general insertion can take it.
    requests = [(0, (5, 0), (9, 0)), (1, (3, 1), (7, 1))]
    m = make_model([(0, 0)], requests, capacity=2, sharing_mode="detour")
    m.step()
    m.step()
    taxi = m.taxis[0]
    p1, p2 = m.passengers
    assert p2.taxi is taxi
    assert taxi.onboard == []  # P1 not picked up yet when P2 was inserted
    assert stops_of(taxi)[0] == (PICKUP, p2.unique_id)
    run(m)
    assert p1.status == p2.status == "completed"
    assert p1.shared and p2.shared
    assert p1.pickup_time - p1.promised_pickup <= m.max_extra_delay

    # Stage 2 (no route change) cannot accept P2 at minute 1.
    m = make_model([(0, 0)], requests, capacity=2, sharing_mode="no_detour")
    m.step()
    m.step()
    assert m.passengers[1].taxi is None


def test_insertion_rejected_when_promised_pickup_slips_too_much():
    # P1 is promised a pickup at (10,0) at minute 10. P2 at (0,10) asks at
    # minute 1. Serving P2 first gives nobody extra in-vehicle time, but P1's
    # pickup would slip by 26 minutes > 10: that plan must be rejected.
    m = make_model([(0, 0)], [(0, (10, 0), (10, 1)), (1, (0, 10), (0, 12))],
                   capacity=2, sharing_mode="detour")
    m.step()
    m.step()
    taxi = m.taxis[0]
    p1, p2 = m.passengers
    assert p1.promised_pickup == 10
    assert stops_of(taxi) == [(PICKUP, p1.unique_id), (DROPOFF, p1.unique_id),
                              (PICKUP, p2.unique_id), (DROPOFF, p2.unique_id)]
    p2_first = [(PICKUP, p2), (DROPOFF, p2), (PICKUP, p1), (DROPOFF, p1)]
    assert taxi.evaluate(p2_first) is None
    promise = taxi.promised_pickup.pop(p1)  # without the promise rule ...
    assert taxi.evaluate(p2_first) is not None  # ... the plan would pass
    taxi.promised_pickup[p1] = promise
    run(m)
    assert p1.pickup_time == 10


def test_boarding_time_single_trip():
    # Taxi at (0,0); passenger (3,0)->(3,4); 1 minute to board, 1 to alight.
    m = make_model([(0, 0)], [(0, (3, 0), (3, 4))], duration=20, boarding_minutes=1)
    for _ in range(3):
        m.step()
    assert m.taxis[0].state == PICKING_UP  # reached the origin at minute 3
    run(m)
    p = m.passengers[0]
    assert p.pickup_time == 3  # taxi reaches the origin, boarding starts
    assert p.arrival_time == 9  # 3 + 1 boarding + 4 driving + 1 alighting
    assert p.individual_time == 6
    assert p.in_vehicle_time == 6
    assert p.extra_delay == 0
    taxi = m.taxis[0]
    assert (taxi.distance, taxi.empty_distance, taxi.occupied_distance) == (7, 3, 4)
    assert p.ride_distance == 4
    assert m.latest_metrics["passenger_distance"] == 4


def test_boarding_time_counts_each_stop_in_same_district():
    # P1 is dropped off at (5,0) where P2 is picked up. Earliest pickup for P2:
    # board P2 first (minute 6-7), then P1 alights (7-8): each stop costs
    # 1 minute, so both passengers get 1 minute of extra delay.
    m = run(make_model([(0, 0)], [(0, (0, 0), (5, 0)), (0, (5, 0), (5, 2))],
                       capacity=2, sharing_mode="detour", boarding_minutes=1))
    p1, p2 = m.passengers
    assert p1.pickup_time == 0
    assert p2.pickup_time == 6  # 1 boarding + 5 driving
    assert p1.arrival_time == 8  # P2 boards 6-7, P1 alights 7-8
    assert p2.arrival_time == 11  # drive 2 + alight 1
    assert p1.extra_delay == 1 and p2.extra_delay == 1
    assert p1.shared and p2.shared


@pytest.mark.parametrize("capacity", [3, 4])
@pytest.mark.parametrize("boarding", [0, 1, 2])
@pytest.mark.parametrize("seed", [1, 2])
def test_large_capacity_never_exceeded(capacity, boarding, seed):
    m = legacy_model(num_taxis=3, num_passengers=80, capacity=capacity,
                  sharing_mode="detour", arrival_mode="gradual", arrival_window=60,
                  duration=90, boarding_minutes=boarding, seed=seed)
    max_onboard = 0
    while m.running:
        m.step()
        max_onboard = max(max_onboard, *(len(t.onboard) for t in m.taxis))
        for t in m.taxis:
            assert len(t.onboard) <= capacity
    run(m)  # model already finished: re-checks invariants once
    assert max_onboard >= 2


def test_three_passengers_on_board_with_capacity_three():
    # Three trips along the same street: all fit in one taxi of capacity 3.
    requests = [(0, (0, 0), (10, 0)), (1, (2, 0), (8, 0)), (2, (4, 0), (9, 0))]
    m = make_model([(0, 0)], requests, capacity=3, sharing_mode="detour")
    max_onboard = 0
    while m.running:
        m.step()
        max_onboard = max(max_onboard, len(m.taxis[0].onboard))
    assert max_onboard == 3
    assert all(p.extra_delay == 0 for p in m.passengers)

    # Capacity 2: the third passenger can be booked, but never rides as third.
    m = make_model([(0, 0)], requests, capacity=2, sharing_mode="detour")
    max_onboard = 0
    while m.running:
        m.step()
        max_onboard = max(max_onboard, len(m.taxis[0].onboard))
    assert max_onboard == 2
    assert all(p.status == "completed" for p in m.passengers)


def test_booking_limit_per_taxi():
    # One taxi of capacity 1, five requests at minute 0: at most
    # BOOKINGS_PER_SEAT * capacity = 2 passengers on board or assigned.
    requests = [(0, (i, 0), (i, 3)) for i in range(1, 6)]
    m = make_model([(0, 0)], requests, capacity=1, sharing_mode="detour")
    m.step()
    taxi = m.taxis[0]
    assert taxi.committed() == 2
    assert sum(p.status == "assigned" or p.status == "travelling"
               for p in m.passengers) == 2
    run(m)


@pytest.mark.parametrize("mode, capacity", [("none", 1), ("no_detour", 2),
                                            ("detour", 2), ("detour", 4)])
def test_distance_split_adds_up(mode, capacity):
    m = run(legacy_model(num_taxis=5, num_passengers=60, capacity=capacity,
                      sharing_mode=mode, arrival_mode="gradual", seed=4,
                      duration=90))
    r = m.latest_metrics
    assert r["empty_distance"] + r["occupied_distance"] == r["total_distance"]
    assert r["passenger_distance"] == sum(p.ride_distance for p in m.passengers)
    assert r["passenger_distance"] >= r["occupied_distance"]
    if mode == "none":
        assert r["passenger_distance"] == r["occupied_distance"]


def test_capacity_must_be_between_one_and_four():
    with pytest.raises(ValueError):
        legacy_model(capacity=5)


BASELINE = Path(__file__).parent / "data" / "baseline_none_no_detour.json"


@pytest.mark.parametrize("case", json.loads(BASELINE.read_text()),
                         ids=lambda c: "{sharing_mode}-{arrival_mode}-{seed}".format(**c["params"]))
def test_none_and_no_detour_unchanged(case):
    """Results recorded with the code before step 1 (stops were instantaneous)
    must be reproduced exactly with boarding_minutes=0."""
    m = run(legacy_model(boarding_minutes=0, **case["params"]))
    for key, expected in case["metrics"].items():
        actual = m.latest_metrics[key]
        if isinstance(expected, float) and math.isnan(expected):
            assert math.isnan(actual), key
        else:
            assert actual == pytest.approx(expected), key
    actual_passengers = [[p.request_time, p.pickup_time, p.arrival_time, p.status]
                         for p in m.passengers]
    assert actual_passengers == case["passengers"]
