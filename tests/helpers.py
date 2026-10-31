"""Shared helpers for deterministic test scenarios."""

from pathlib import Path

import pandas as pd

from agents import (ABANDONED, ASSIGNED, COMPLETED, DROPOFF, NOT_COMPLETED, PICKUP,
                    TRAVELLING, WAITING)
from model import TaxiModel


# The defaults the tests were written for (before the fixed 30x30 study
# settings): tests that build random scenarios use these explicitly, so they
# keep running exactly the same scenarios.
OLD_DEFAULTS = {"width": 20, "height": 20, "num_taxis": 5, "num_passengers": 40,
                "arrival_mode": "all_at_start", "arrival_window": 60,
                "duration": 60}


def legacy_model(**kwargs):
    """TaxiModel with OLD_DEFAULTS for every parameter not given."""
    return TaxiModel(**{**OLD_DEFAULTS, **kwargs})


ROOT = Path(__file__).resolve().parent.parent
BASE_IDS = ["S1", "S2", "S3", "S4"]  # experiments.csv rows with every feature off


def assert_reproduces_stored(tmp_path, edit=None, seeds=None):
    """Re-run S1-S4 from experiments.csv (after `edit(configs)`, e.g. adding
    explicit "off" columns) and check that every value stored in results/
    for them is reproduced exactly; only new columns may be added. With
    `seeds`, only those runs are compared (summary.csv needs all seeds)."""
    import run_experiments

    configs = pd.read_csv(ROOT / "experiments.csv")
    configs = configs[configs["config_id"].isin(BASE_IDS)]
    assert not configs[["buses", "walking", "congestion", "patience"]].any().any()
    if edit is not None:
        configs = edit(configs.copy())
    path = tmp_path / "configs.csv"
    configs.to_csv(path, index=False)
    out = tmp_path / "out"
    run_experiments.run(path, out=out, charts=False,
                        **({} if seeds is None else {"seeds": seeds}))
    names = ["runs.csv", "passengers.csv"] + (["summary.csv"] if seeds is None else [])
    for name in names:
        stored = pd.read_csv(ROOT / "results" / name)
        stored = stored[stored["config_id"].isin(BASE_IDS)]
        if seeds is not None:
            stored = stored[stored["seed"].isin(seeds)]
        stored = stored.reset_index(drop=True)
        fresh = pd.read_csv(out / name)
        assert len(stored) and set(stored.columns) <= set(fresh.columns), name
        # Values must match exactly. dtypes may differ: in the stored file a
        # column such as individual_time is float because other scenarios'
        # bus passengers leave it empty, while S1-S4 alone read back as int.
        pd.testing.assert_frame_equal(fresh[stored.columns], stored,
                                      check_exact=True, check_dtype=False, obj=name)


def make_model(taxi_starts, requests, **kwargs):
    # Hand-computed expected times in the scenario tests assume instantaneous
    # stops unless a test passes boarding_minutes explicitly, and a 20x20 grid
    # (it fixes the congestion zone and the walking neighbours at the edges).
    params = {"duration": 60, "capacity": 1, "sharing_mode": "none",
              "boarding_minutes": 0, "width": 20, "height": 20}
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
    for bus in model.buses:
        assert len(bus.onboard) <= bus.capacity
        assert bus.pos == bus.line.cells[bus.index]
        for p in bus.onboard:
            assert p.mode == "bus" and p.pos == bus.pos
            assert p.status in (TRAVELLING, NOT_COMPLETED)
    for p in model.passengers:
        if p.mode == "bus":
            assert p.taxi is None and p.patience is None
        if p.status == COMPLETED:
            assert p.pickup_time is not None
            assert p.request_time <= p.pickup_time <= p.arrival_time <= model.duration
            assert p.pos is None  # removed from the grid
            if p.mode == "taxi":
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


__all__ = ["make_model", "legacy_model", "OLD_DEFAULTS", "run", "check_invariants",
           "stops_of", "PICKUP", "DROPOFF"]
