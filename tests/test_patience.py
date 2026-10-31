"""Passenger acceptability: patience, abandonment and acceptable trips."""

import pandas as pd
import pytest

import run_experiments
from agents import ABANDONED, ASSIGNED, COMPLETED, WAITING
from helpers import assert_reproduces_stored, legacy_model, make_model, run
from messages import ACCEPT, PROPOSE
from model import TaxiModel


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
    # A is promised a pickup at minute 4 (within patience 5). B is then
    # inserted before A (detour, boarding 1 min), which pushes A's pickup to
    # minute 8: past A's patience but within the promise rule. A is assigned,
    # so A keeps waiting and completes.
    m = make_model([(0, 0)], [(0, (4, 0), (4, 5)), (0, (2, 0), (2, 1))],
                   duration=30, capacity=2, sharing_mode="detour",
                   boarding_minutes=1, patience_min=5, patience_max=5)
    a, b = m.passengers
    m.step()
    assert a.status == b.status == ASSIGNED
    assert a.promised_pickup == 4
    run(m)
    assert a.status == b.status == COMPLETED
    assert a.waiting_time == 8 > a.patience
    r = m.latest_metrics
    assert r["abandoned"] == 0
    assert r["completed_pct"] == 100
    assert r["acceptable_pct"] == 50  # A completed, but waited past patience


def test_passenger_ignores_taxi_beyond_patience():
    # The only taxi is 10 minutes away; with patience 5 the passenger never
    # accepts its proposal and gives up at minute 5.
    m = make_model([(0, 0)], [(0, (10, 0), (10, 3))], duration=30,
                   patience_min=5, patience_max=5)
    p = m.passengers[0]
    run(m)
    assert m.message_counts[ACCEPT] == 0
    assert m.message_counts[PROPOSE] == 5  # one proposal per minute 0-4
    assert p.status == ABANDONED
    assert p.abandon_time == 5
    assert m.taxis[0].distance == 0


def test_passenger_accepts_taxi_within_patience():
    m = run(make_model([(0, 0)], [(0, (3, 0), (3, 2))], duration=30,
                       patience_min=5, patience_max=5))
    p = m.passengers[0]
    assert p.status == COMPLETED
    assert p.promised_pickup == p.pickup_time == 3
    assert m.latest_metrics["acceptable_pct"] == 100


def test_ui_checkboxes_map_to_model_parameters():
    """The UI's Reset path (Mesa's own kwargs builder) with the checkboxes."""
    from mesa.visualization.solara_viz import (_build_model_init_kwargs,
                                               _check_model_params)

    from app import UITaxiModel, model_params

    model = UITaxiModel()
    _check_model_params(model, model_params)  # what SolaraViz checks
    assert (model.patience_max, model.congestion, model.walk_radius,
            model.buses_on) == (None, "off", 0, False)
    assert (model.width, model.height, model.duration) == (30, 30, 120)
    params = {"num_passengers": 30, "seed": 7, "patience": True,
              "congestion": True, "walking": True, "buses": True}
    kwargs = _build_model_init_kwargs(model, params, add_scenario_when_empty=True,
                                      require_model_accepts_scenario=True)
    new = type(model)(**kwargs)
    assert (new.patience_min, new.patience_max, new.seed) == (10, 30, 7)
    assert (new.congestion, new.walk_radius, new.buses_on) == ("center", 1, True)
    assert all(p.patience is None or 10 <= p.patience <= 30 for p in new.passengers)


def test_patience_disabled_by_default_and_by_zero():
    for kwargs in ({}, {"patience_max": None}, {"patience_max": 0}):
        m = legacy_model(num_passengers=60, arrival_mode="gradual", **kwargs)
        assert all(p.patience is None for p in m.passengers)
        assert m.patience_max is None


def test_patience_keeps_demand_identical():
    params = dict(num_taxis=3, num_passengers=60, capacity=2, sharing_mode="detour",
                  arrival_mode="gradual", duration=60, seed=3)
    plain = run(legacy_model(**params))
    patient = run(legacy_model(patience_min=3, patience_max=8, **params))
    trip = lambda p: (p.request_time, p.origin, p.destination)  # noqa: E731
    assert [trip(p) for p in plain.passengers] == [trip(p) for p in patient.passengers]
    assert all(3 <= p.patience <= 8 for p in patient.passengers)
    assert patient.latest_metrics["abandoned"] > 0
    # Same seed, same draws.
    again = legacy_model(patience_min=3, patience_max=8, **params)
    assert ([p.patience for p in again.passengers]
            == [p.patience for p in patient.passengers[:len(again.passengers)]])


def test_invalid_patience_range():
    with pytest.raises(ValueError):
        legacy_model(patience_min=5, patience_max=3)
    with pytest.raises(ValueError):
        legacy_model(patience_min=0, patience_max=3)


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
    """With every feature at its default (off: the four feature columns
    removed), S1-S4 reproduce every value stored in results/ for all seeds,
    including summary.csv; only new columns may be added."""
    assert_reproduces_stored(
        tmp_path,
        edit=lambda c: c.drop(columns=["buses", "walking", "congestion", "patience"]))
