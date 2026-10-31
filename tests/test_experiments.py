"""Experiment runner and CSV export."""

import pytest

import pandas as pd

import run_experiments
from model import TaxiModel


def test_experiment_csv_outputs(tmp_path):
    config = tmp_path / "configs.csv"
    config.write_text(
        "config_id,description,num_taxis,num_passengers,capacity,sharing_mode,"
        "arrival_mode,arrival_window,duration\n"
        "A,single,3,15,1,none,all_at_start,30,30\n"
        "B,detour,3,15,2,detour,gradual,20,30\n"
    )
    out = tmp_path / "out"
    run_experiments.run(config, seeds=[1, 2], out=out)

    runs = pd.read_csv(out / "runs.csv")
    summary = pd.read_csv(out / "summary.csv")
    passengers = pd.read_csv(out / "passengers.csv")
    assert len(runs) == 4  # 2 configs x 2 seeds
    assert list(summary["config_id"]) == ["A", "B"]
    assert (summary["seeds"] == 2).all()
    assert (summary["max_extra_delay_limit"] == 10).all()
    assert len(passengers) == runs["created"].sum()
    assert (runs["steps"] == 30).all()
    assert (runs["completed"] + runs["not_completed"] == runs["created"]).all()
    assert ((runs["empty_distance"] + runs["occupied_distance"])
            == runs["total_distance"]).all()
    assert (runs["boarding_minutes"] == 1).all()  # default when column absent
    for name in ["empty_distance_pct_mean", "avg_occupancy_mean",
                 "passenger_distance_mean"]:
        assert name in summary.columns
    ride = passengers.groupby(["config_id", "seed"])["ride_distance"].sum()
    assert (ride.values == runs.set_index(["config_id", "seed"])
            .loc[ride.index, "passenger_distance"].values).all()
    assert set(passengers["status"]) <= {"completed", "not_completed"}
    for name in ["comparison", "completed_pct", "avg_wait_completed"]:
        assert (out / "charts" / f"{name}.png").stat().st_size > 0

    # CSV values equal a direct run of the same configuration.
    m = TaxiModel(num_taxis=3, num_passengers=15, capacity=2, sharing_mode="detour",
                  arrival_mode="gradual", arrival_window=20, duration=30, seed=2)
    while m.running:
        m.step()
    row = runs[(runs.config_id == "B") & (runs.seed == 2)].iloc[0]
    for key in ["completed", "not_completed", "total_distance", "messages",
                "empty_distance", "passenger_distance"]:
        assert row[key] == m.latest_metrics[key]
    done = passengers[(passengers.config_id == "B") & (passengers.seed == 2)
                      & (passengers.status == "completed")]
    assert len(done) == m.latest_metrics["completed"]
    assert abs(done["waiting_time"].mean() - m.latest_metrics["avg_wait_completed"]) < 1e-9

    summary_b = summary.set_index("config_id").loc["B"]
    assert abs(summary_b["completed_mean"]
               - runs[runs.config_id == "B"]["completed"].mean()) < 1e-9


@pytest.mark.parametrize("congestion_on,congestion_off", [("True", "False"),
                                                          ("center", "off")])
def test_feature_columns_map_like_the_sidebar(tmp_path, congestion_on,
                                              congestion_off):
    config = tmp_path / "configs.csv"
    config.write_text(
        "config_id,description,num_taxis,num_passengers,capacity,sharing_mode,"
        "buses,walking,congestion,patience\n"
        f"A,all off,6,90,2,detour,False,False,{congestion_off},False\n"
        f"B,all on,6,90,2,detour,True,True,{congestion_on},True\n"
    )
    runs, _, _ = run_experiments.run(config, seeds=[1], out=tmp_path, charts=False)
    a, b = runs.set_index("config_id").loc["A"], runs.set_index("config_id").loc["B"]
    assert (a["buses"], a["walk_radius"], a["congestion"]) == (False, 0, "off")
    assert pd.isna(a["patience_max"])
    assert (b["buses"], b["walk_radius"], b["congestion"]) == (True, 1, "center")
    assert (b["patience_min"], b["patience_max"]) == (10, 30)
    # Fixed settings from config.py when the columns are absent.
    assert (b["width"], b["height"], b["duration"], b["arrival_mode"]) == (
        30, 30, 120, "gradual")
    assert b["bus_share_pct"] > 0
