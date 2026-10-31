"""Shared helpers for deterministic test scenarios."""

from agents import (ABANDONED, ASSIGNED, COMPLETED, DROPOFF, NOT_COMPLETED, PICKUP,
                    TRAVELLING, WAITING)
from model import TaxiModel


def make_model(taxi_starts, requests, **kwargs):
    # Hand-computed expected times in the scenario tests assume instantaneous
    # stops unless a test passes boarding_minutes explicitly.
    params = {"duration": 60, "capacity": 1, "sharing_mode": "none",
              "boarding_minutes": 0}
    params.update(kwargs)
    return TaxiModel(taxi_starts=taxi_starts, requests=requests, **params)


def check_invariants(model):
    """Properties that must hold after every step."""
    for taxi in model.taxis:
        assert len(taxi.onboard) <= taxi.capacity
        assert taxi.empty_distance + taxi.occupied_distance == taxi.distance
        for p in taxi.onboard:
            assert p.status in (TRAVELLING, NOT_COMPLETED)
            assert p.pos == taxi.pos
        # Every planned drop-off comes after its pickup (or the passenger is on board).
        seen_pickups = set(taxi.onboard)
        for kind, p in taxi.stops:
            if kind == PICKUP:
                seen_pickups.add(p)
            else:
                assert p in seen_pickups
    for p in model.passengers:
        if p.status == COMPLETED:
            assert p.pickup_time is not None
            assert p.request_time <= p.pickup_time <= p.arrival_time <= model.duration
            assert p.pos is None  # removed from the grid
            assert p.extra_delay <= model.max_extra_delay
        if p.status in (WAITING, ASSIGNED):
            assert p.pickup_time is None
        if p.status == ABANDONED:
            assert p.pos is None and p.pickup_time is None
            assert p.abandon_time - p.request_time == p.patience
            assert all(q is not p for taxi in model.taxis for _, q in taxi.stops)
        if p.pickup_time is not None and p.promised_pickup is not None:
            # Acceptability: pickup never slips more than MAX past the promise.
            assert p.pickup_time - p.promised_pickup <= model.max_extra_delay
    statuses = [p.status for p in model.passengers]
    m = model.latest_metrics
    assert m["created"] == len(statuses)
    assert (
        m["waiting"] + m["assigned"] + m["travelling"] + m["completed"]
        + m["not_completed"] + m["abandoned"]
    ) == m["created"]
    assert m["empty_distance"] + m["occupied_distance"] == m["total_distance"]


def run(model):
    while model.running:
        model.step()
        check_invariants(model)
    return model


def stops_of(taxi):
    return [(kind, p.unique_id) for kind, p in taxi.stops]


__all__ = ["make_model", "run", "check_invariants", "stops_of", "PICKUP", "DROPOFF"]
