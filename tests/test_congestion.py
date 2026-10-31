"""Optional traffic congestion: integer cell costs used by movement and planning."""

import pytest

from agents import COMPLETED
from helpers import assert_reproduces_stored, legacy_model, make_model, run
from routing import congestion_factor


def test_congestion_zones_on_default_grid():
    # 20x20: centre square x, y in 7..12, ring 6..13.
    factor = lambda cell: congestion_factor(cell, 20, 20, "center")  # noqa: E731
    assert factor((7, 7)) == factor((12, 12)) == factor((10, 9)) == 3
    assert factor((6, 6)) == factor((13, 10)) == factor((9, 13)) == 2
    assert factor((5, 10)) == factor((14, 14)) == factor((0, 0)) == 1
    assert congestion_factor((10, 10), 20, 20, "off") == 1
    with pytest.raises(ValueError):
        legacy_model(congestion="rush_hour")


def test_trip_through_centre_takes_longer():
    # Both trips are 10 districts. Through the centre (y=10): cell 6 costs 2,
    # cells 7-12 cost 3 each, 13 costs 2, 14-15 cost 1 -> 24 minutes.
    def solo(origin, destination):
        m = run(make_model([origin], [(0, origin, destination)], duration=60,
                           congestion="center"))
        p = m.passengers[0]
        assert p.status == COMPLETED
        return p

    centre = solo((5, 10), (15, 10))
    edge = solo((5, 1), (15, 1))
    assert edge.in_vehicle_time == 10
    assert centre.in_vehicle_time == 24
    # The baseline uses the same costs: a solo direct trip has no extra delay.
    assert centre.individual_time == 24
    assert centre.extra_delay == edge.extra_delay == 0


def test_estimates_exact_while_taxi_is_inside_a_slow_cell():
    # The taxi drives to A through the centre. B requests at minute 3 when the
    # taxi has already spent 1 of the 3 minutes needed to enter (7, 10); the
    # estimate credits that minute, so promises equal the actual pickups.
    m = make_model([(5, 10)], [(0, (15, 10), (16, 10)), (3, (10, 10), (11, 10))],
                   duration=60, capacity=2, sharing_mode="detour",
                   congestion="center")
    run(m)
    a, b = m.passengers
    assert a.promised_pickup == a.pickup_time == 24
    assert b.promised_pickup == b.pickup_time == 14
    assert (b.arrival_time, a.arrival_time) == (17, 25)
    assert a.extra_delay == b.extra_delay == 0


@pytest.mark.parametrize("capacity", [2, 4])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_limits_hold_under_congestion(capacity, seed):
    # helpers.run checks after every step that no pickup slips more than
    # MAX_EXTRA_DELAY_MINUTES past its promise and every completed passenger
    # has extra delay <= MAX_EXTRA_DELAY_MINUTES.
    m = run(legacy_model(num_taxis=5, num_passengers=60, capacity=capacity,
                      sharing_mode="detour", arrival_mode="gradual", duration=90,
                      congestion="center", seed=seed))
    r = m.latest_metrics
    assert r["shared_completed"] > 0
    assert r["max_extra_delay"] <= m.max_extra_delay


def test_no_detour_promises_exact_under_congestion():
    # With instantaneous stops, no_detour insertions never delay anyone, so
    # every pickup happens exactly at the promised minute.
    m = run(legacy_model(num_taxis=5, num_passengers=60, capacity=2,
                      sharing_mode="no_detour", arrival_mode="gradual",
                      duration=90, boarding_minutes=0, congestion="center", seed=2))
    picked = [p for p in m.passengers if p.pickup_time is not None]
    assert picked
    assert all(p.pickup_time == p.promised_pickup for p in picked)


def test_congestion_off_reproduces_results(tmp_path):
    """An explicit congestion = "off" column (the older string format)
    reproduces the stored S1-S4 values (seeds 1-2)."""
    def explicit_off(configs):
        configs["congestion"] = "off"
        return configs

    assert_reproduces_stored(tmp_path, edit=explicit_off, seeds=[1, 2])
