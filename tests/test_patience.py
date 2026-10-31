"""Passenger acceptability: patience, abandonment and acceptable trips."""

from pathlib import Path

import pandas as pd
import pytest

import run_experiments
from agents import ABANDONED, ASSIGNED, COMPLETED, WAITING
from helpers import make_model, run
from model import TaxiModel

ROOT = Path(__file__).resolve().parent.parent


def test_waiting_passenger_abandons_after_patience():
    # One single-seat taxi takes passenger 0 (lower id wins the CONFIRM);
    # passenger 1 never finds a free taxi and gives up at minute 2.
    m = make_model([(0, 0)], [(0, (0, 0), (15, 0)), (0, (5, 5), (6, 6))],
                   duration=20, patience_min=2, patience_max=2)
    rider, quitter = m.passengers
    m.step()
    assert quitter.status == WAITING
    m.step()
    assert m.minute == 2
    assert quitter.status == ABANDONED
    assert quitter.abandon_time == 2
    assert quitter.pos is None
    assert m.latest_metrics["abandoned"] == 1
    run(m)
    assert rider.status == COMPLETED
    r = m.latest_metrics
    assert (r["completed"], r["abandoned"], r["not_completed"]) == (1, 1, 0)
    assert r["abandoned_pct"] == 50
    assert r["acceptable_pct"] == 50  # rider waited 0 <= 2 with no extra delay


def test_assigned_passenger_never_abandons():
    # The taxi is 10 minutes away, far beyond the 2-minute patience, but the
    # passenger is confirmed at minute 0 and keeps waiting.
    m = make_model([(0, 0)], [(0, (10, 0), (10, 3))], duration=30,
                   patience_min=2, patience_max=2)
    p = m.passengers[0]
    m.step()
    assert p.status == ASSIGNED
    run(m)
    assert p.status == COMPLETED
    assert p.waiting_time == 10
    r = m.latest_metrics
    assert r["abandoned"] == 0
    assert r["completed_pct"] == 100
    assert r["acceptable_pct"] == 0  # completed, but waited longer than patience


def test_patience_disabled_by_default_and_by_zero():
    for kwargs in ({}, {"patience_max": None}, {"patience_max": 0}):
        m = TaxiModel(num_passengers=60, arrival_mode="gradual", **kwargs)
        assert all(p.patience is None for p in m.passengers)
        assert m.patience_max is None


def test_patience_keeps_demand_identical():
    params = dict(num_taxis=3, num_passengers=60, capacity=2, sharing_mode="detour",
                  arrival_mode="gradual", duration=60, seed=3)
    plain = run(TaxiModel(**params))
    patient = run(TaxiModel(patience_min=3, patience_max=8, **params))
    trip = lambda p: (p.request_time, p.origin, p.destination)  # noqa: E731
    assert [trip(p) for p in plain.passengers] == [trip(p) for p in patient.passengers]
    assert all(3 <= p.patience <= 8 for p in patient.passengers)
    assert patient.latest_metrics["abandoned"] > 0
    # Same seed, same draws.
    again = TaxiModel(patience_min=3, patience_max=8, **params)
    assert ([p.patience for p in again.passengers]
            == [p.patience for p in patient.passengers[:len(again.passengers)]])


def test_invalid_patience_range():
    with pytest.raises(ValueError):
        TaxiModel(patience_min=5, patience_max=3)
    with pytest.raises(ValueError):
        TaxiModel(patience_min=0, patience_max=3)


def test_optional_patience_columns(tmp_path):
    config = tmp_path / "configs.csv"
    config.write_text(
        "config_id,description,num_taxis,num_passengers,capacity,sharing_mode,"
        "arrival_mode,arrival_window,duration,patience_min,patience_max\n"
        "A,off,2,20,1,none,all_at_start,30,30,3,\n"
        "B,on,2,20,1,none,all_at_start,30,30,3,6\n"
    )
    runs, passengers, summary = run_experiments.run(config, seeds=[1], out=tmp_path,
                                                    charts=False)
    runs = runs.set_index("config_id")
    assert pd.isna(runs.loc["A", "patience_max"])
    assert runs.loc["A", "abandoned"] == 0
    assert runs.loc["B", "abandoned"] > 0
    b = passengers[passengers.config_id == "B"]
    assert ((b["patience"] >= 3) & (b["patience"] <= 6)).all()
    assert "acceptable_pct_mean" in summary.columns


def test_default_results_unchanged(tmp_path):
    """With patience disabled (the default), regenerating results/ reproduces
    every value already stored there; only new columns may be added."""
    run_experiments.run(ROOT / "experiments.csv", out=tmp_path, charts=False)
    for name in ["runs.csv", "summary.csv", "passengers.csv"]:
        stored = pd.read_csv(ROOT / "results" / name)
        fresh = pd.read_csv(tmp_path / name)
        assert set(stored.columns) <= set(fresh.columns), name
        pd.testing.assert_frame_equal(fresh[stored.columns], stored,
                                      check_exact=True, obj=name)
