"""Stages 2 and 3: capacity two, sharing without and with route changes.

Common setup: one taxi at (0,0). Passenger 1 is picked up at minute 0 and goes
from (0,0) to (10,0) (direct trip 10 minutes). At minute 1, when the taxi is at
(1,0), passenger 2 requests a ride.
"""

import pytest

from agents import COMPLETED, DROPOFF, PICKUP
from config import MAX_EXTRA_DELAY_MINUTES
from helpers import legacy_model, make_model, run, stops_of

P1 = (0, (0, 0), (10, 0))


def scenario(p2, **kwargs):
    return make_model([(0, 0)], [P1, (1,) + p2], **kwargs)


def test_threshold_is_fixed_at_ten():
    assert MAX_EXTRA_DELAY_MINUTES == 10
    assert legacy_model().max_extra_delay == 10


@pytest.mark.parametrize(
    "capacity, mode", [(1, "none"), (2, "none"), (1, "no_detour"), (1, "detour")]
)
def test_without_sharing_second_passenger_waits(capacity, mode):
    m = run(scenario(((3, 0), (6, 0)), capacity=capacity, sharing_mode=mode))
    p1, p2 = m.passengers
    assert p1.arrival_time == 10
    # Taxi becomes free at (10,0) at minute 10, drives back 7 districts.
    assert p2.pickup_time == 17
    assert p2.arrival_time == 20
    assert not p1.shared and not p2.shared


def test_capacity_two_on_route_without_route_change():
    m = scenario(((3, 0), (6, 0)), capacity=2, sharing_mode="no_detour")
    m.step()  # minute 0: P1 picked up
    route_before = m.taxis[0].route_cells()
    m.step()  # minute 1: P2 accepted
    taxi = m.taxis[0]
    p1, p2 = m.passengers
    assert p2.taxi is taxi
    assert stops_of(taxi) == [
        (PICKUP, p2.unique_id), (DROPOFF, p2.unique_id), (DROPOFF, p1.unique_id)
    ]
    assert taxi.route_cells() == route_before[1:]  # same cells, one step further
    run(m)
    assert (p2.pickup_time, p2.arrival_time) == (3, 6)
    assert p1.arrival_time == 10
    assert p1.extra_delay == 0 and p2.extra_delay == 0
    assert p1.shared and p2.shared


def test_no_detour_rejects_trip_off_route():
    m = run(scenario(((3, 2), (6, 2)), capacity=2, sharing_mode="no_detour"))
    p1, p2 = m.passengers
    assert not p2.shared
    assert p1.arrival_time == 10
    assert p2.pickup_time == 19  # served only after P1, from (10,0)


def test_detour_sharing_accepted_within_threshold():
    m = run(scenario(((3, 2), (6, 2)), capacity=2, sharing_mode="detour"))
    p1, p2 = m.passengers
    assert p1.status == COMPLETED and p2.status == COMPLETED
    assert p1.shared and p2.shared
    # Best order: pick P2, drop P2, drop P1.
    assert (p2.pickup_time, p2.arrival_time) == (5, 8)
    assert p1.arrival_time == 14
    assert p1.extra_delay == 4 <= MAX_EXTRA_DELAY_MINUTES
    assert p2.extra_delay == 0


def test_detour_sharing_rejected_when_delay_too_large():
    m = scenario(((3, 8), (6, 8)), capacity=2, sharing_mode="detour")
    m.step()
    m.step()  # P2 asks at minute 1; serving them would delay P1 by > 10 min
    taxi = m.taxis[0]
    p1, p2 = m.passengers
    # Every plan that picks P2 up before P1's drop-off is rejected. The general
    # insertion search (stage 3-4) still queues P2 AFTER P1: P1's route and
    # drop-off stay first and unchanged.
    assert stops_of(taxi) == [
        (DROPOFF, p1.unique_id), (PICKUP, p2.unique_id), (DROPOFF, p2.unique_id)
    ]
    assert p2.taxi is taxi
    run(m)
    assert p1.arrival_time == 10 and p1.extra_delay == 0
    assert not p2.shared
    assert p2.pickup_time == 25  # after P1: from (10,0) to (3,8) = 15 minutes


def test_detour_for_second_destination():
    # P2 is picked up on P1's route, but their destination needs a detour.
    m = scenario(((3, 0), (5, 4)), capacity=2, sharing_mode="no_detour")
    m.step()
    m.step()
    assert m.passengers[1].taxi is None  # stage 2 cannot accept it

    m = run(scenario(((3, 0), (5, 4)), capacity=2, sharing_mode="detour"))
    p1, p2 = m.passengers
    assert p1.shared and p2.shared
    assert (p2.pickup_time, p2.arrival_time) == (3, 9)
    assert p1.arrival_time == 18
    assert p1.extra_delay == 8
    assert p2.extra_delay == 0


def test_capacity_never_exceeded():
    # P2 and P3 both lie on the route, but only one seat is free.
    m = make_model(
        [(0, 0)],
        [P1, (1, (3, 0), (6, 0)), (1, (4, 0), (7, 0))],
        capacity=2,
        sharing_mode="no_detour",
    )
    max_onboard = 0
    while m.running:
        m.step()
        max_onboard = max(max_onboard, len(m.taxis[0].onboard))
    p1, p2, p3 = m.passengers
    assert max_onboard == 2
    assert p2.pickup_time == 3
    assert p3.pickup_time == 16  # only after the taxi is free at (10,0)


@pytest.mark.parametrize("mode, capacity", [("none", 1), ("no_detour", 2), ("detour", 2)])
@pytest.mark.parametrize("arrival", ["all_at_start", "gradual"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_invariants_random_scenarios(mode, capacity, arrival, seed):
    """run() checks capacity, pickup-before-drop-off, status consistency and
    the delay threshold after every step."""
    m = run(legacy_model(num_taxis=4, num_passengers=50, capacity=capacity,
                      sharing_mode=mode, arrival_mode=arrival, arrival_window=60,
                      duration=90, seed=seed))
    assert m.minute == 90
    assert m.latest_metrics["completed"] > 0
    if mode == "none":
        assert m.latest_metrics["shared_completed"] == 0
