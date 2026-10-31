"""Run the experiment configurations and export CSV results and charts.

Usage (from the project folder):
    python run_experiments.py                       # all configs, seeds 1-10
    python run_experiments.py --only S3 S6          # selected configs
    python run_experiments.py --seeds 1 2 --out results_quick

Each configuration is run with Mesa's batch_run once per seed. The same seed
gives the same passengers and taxi start cells in every configuration, so the
configurations are compared on identical demand where their sizes allow.
MAX_EXTRA_DELAY_MINUTES is never part of a configuration: it stays fixed.

Columns of experiments.csv:
    required  config_id, description, num_taxis, num_passengers, capacity,
              sharing_mode
    features  buses, walking, congestion, patience: optional booleans, mapped
              to model parameters exactly like the sidebar checkboxes
              (config.feature_params); absent = off
    optional  any other model parameter (OPTIONAL_COLUMNS: duration,
              arrival_mode, width, walk_radius, patience_max, ...), so older
              files keep working; absent = the fixed default from config.py.
              A "congestion" column may hold True/False or "off"/"center";
              an empty patience_max cell disables abandonment for that row.

Outputs (in --out, default "results"):
    runs.csv        one row per configuration and seed (all model metrics)
    summary.csv     mean and standard deviation over seeds per configuration
    passengers.csv  one row per passenger per run (final state)
    charts/*.png    comparison bar charts (mean +/- std over seeds)
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from mesa import batch_run

import metrics
from config import (BOARDING_MINUTES, DEFAULTS, FEATURES, MAX_EXTRA_DELAY_MINUTES,
                    PATIENCE_MAX, PATIENCE_MIN, WALK_MINUTES_PER_DISTRICT,
                    feature_params)
from model import TaxiModel

CONFIG_COLUMNS = ["num_taxis", "num_passengers", "capacity", "sharing_mode"]
# Optional columns: when absent, the model default from config.py is used.
OPTIONAL_COLUMNS = {
    "arrival_mode": DEFAULTS["arrival_mode"],
    "arrival_window": DEFAULTS["arrival_window"],
    "duration": DEFAULTS["duration"],
    "boarding_minutes": BOARDING_MINUTES,
    "patience_min": PATIENCE_MIN,
    "patience_max": PATIENCE_MAX,
    "congestion": DEFAULTS["congestion"],
    "walk_radius": DEFAULTS["walk_radius"],
    "walk_minutes_per_district": WALK_MINUTES_PER_DISTRICT,
    "width": DEFAULTS["width"],
    "height": DEFAULTS["height"],
    "buses": DEFAULTS["buses"],
}
PARAM_COLUMNS = CONFIG_COLUMNS + list(OPTIONAL_COLUMNS)

# Metrics summarised across seeds (label used in charts).
SUMMARY_METRICS = {
    "created": "Passengers created",
    "completed": "Passengers completed",
    "completed_pct": "Completed (%)",
    "not_completed": "Not completed",
    "abandoned": "Abandoned (patience exceeded)",
    "abandoned_pct": "Abandoned (%)",
    "acceptable_pct": "Acceptable trips (% of created)",
    "avg_wait_completed": "Avg waiting time, completed (min)",
    "avg_in_vehicle_completed": "Avg in-vehicle time, completed (min)",
    "avg_total_completed": "Avg total journey time, completed (min)",
    "avg_extra_delay_completed": "Avg extra delay, completed (min)",
    "shared_completed": "Completed passengers who shared",
    "avg_extra_delay_shared": "Avg extra delay, shared rides (min)",
    "max_extra_delay": "Max extra delay (min)",
    "avg_wait_censored": "Avg waiting incl. unserved (min)",
    "walked_pct": "Completed passengers who walked (%)",
    "avg_walk_minutes": "Avg walking time, completed (min)",
    "bus_share_pct": "Passengers taking the bus (%)",
    "completed_pct_taxi": "Completed, taxi passengers (%)",
    "completed_pct_bus": "Completed, bus passengers (%)",
    "avg_wait_completed_taxi": "Avg waiting time, taxi, completed (min)",
    "avg_wait_completed_bus": "Avg waiting time, bus, completed (min)",
    "avg_total_completed_taxi": "Avg total journey time, taxi, completed (min)",
    "avg_total_completed_bus": "Avg total journey time, bus, completed (min)",
    "bus_distance": "Bus distance (districts)",
    "avg_bus_occupancy": "Avg bus occupancy (passenger / bus distance)",
    "total_distance": "Total taxi distance (districts)",
    "empty_distance": "Empty taxi distance (districts)",
    "occupied_distance": "Occupied taxi distance (districts)",
    "empty_distance_pct": "Empty share of taxi distance (%)",
    "passenger_distance": "Passenger distance (passenger-districts)",
    "avg_occupancy": "Avg occupancy (passenger / taxi distance)",
    "distance_per_completed": "Taxi distance per completed passenger (districts)",
    "utilization_pct": "Taxi utilization (%)",
}

SEEDS = tuple(range(1, 11))  # default seeds: 1-10

CHART_METRICS = ["completed_pct", "avg_wait_completed", "avg_total_completed",
                 "avg_extra_delay_completed", "distance_per_completed",
                 "empty_distance_pct", "bus_share_pct", "acceptable_pct"]

# Categorical colours by sharing mode (fixed order) plus hatching, so the modes
# stay distinguishable without colour.
MODE_STYLE = {
    "none": ("#2a78d6", ""),
    "no_detour": ("#eb6834", "//"),
    "detour": ("#1baf7a", ".."),
}


# Model parameters set by each feature column (see config.feature_params).
FEATURE_KEYS = {"buses": ["buses"], "walking": ["walk_radius"],
                "congestion": ["congestion"],
                "patience": ["patience_min", "patience_max"]}
assert set(FEATURE_KEYS) == set(FEATURES)


def apply_features(configs):
    """Turn the boolean feature columns into model parameters, like the UI."""
    configs = configs.copy()
    for feature, keys in FEATURE_KEYS.items():
        if feature not in configs.columns:
            continue
        if feature == "congestion" and all(isinstance(v, str)
                                           for v in configs[feature]):
            continue  # an older file with "off"/"center" values
        rows = [feature_params(**{feature: bool(v)}) for v in configs[feature]]
        if feature not in keys:
            configs = configs.drop(columns=feature)  # "walking", "patience"
        for key in keys:
            configs[key] = pd.Series([r[key] for r in rows], index=configs.index,
                                     dtype=object)
    return configs


def load_configs(path, only=None):
    configs = pd.read_csv(path)
    if only:
        configs = configs[configs["config_id"].isin(only)]
        if configs.empty:
            raise SystemExit(f"No configuration matches {only}")
    configs = apply_features(configs)
    for column, default in OPTIONAL_COLUMNS.items():
        if column not in configs.columns:
            configs[column] = default
    return configs


def run_config(row, seeds):
    """Run one configuration for every seed with Mesa's batch_run."""
    params = {col: row[col] for col in PARAM_COLUMNS}
    params = {k: (v.item() if hasattr(v, "item") else v) for k, v in params.items()}
    params = {k: (None if pd.isna(v) else v) for k, v in params.items()}  # empty cell
    records = batch_run(
        TaxiModel,
        parameters=params,
        rng=seeds,  # passed to TaxiModel(seed=...)
        max_steps=int(params["duration"]),
        data_collection_period=-1,  # final state only
        display_progress=False,
    )
    df = pd.DataFrame(records)
    df.insert(0, "config_id", row["config_id"])
    df.insert(1, "description", row["description"])
    return df


def split_records(df):
    run_cols = (["config_id", "description", "seed"] + PARAM_COLUMNS
                + ["Step"] + metrics.MODEL_METRICS)
    runs = df[run_cols].drop_duplicates(subset=["config_id", "seed"])
    runs = runs.rename(columns={"Step": "steps"}).reset_index(drop=True)
    passenger_cols = ["config_id", "seed"] + list(metrics.PASSENGER_REPORTERS)
    if "passenger_id" in df.columns:
        passengers = df.dropna(subset=["passenger_id"])[passenger_cols]
    else:
        passengers = pd.DataFrame(columns=passenger_cols)
    return runs, passengers.reset_index(drop=True)


def summarise(runs, configs):
    grouped = runs.groupby("config_id", sort=False)
    summary = configs.set_index("config_id")[["description"] + PARAM_COLUMNS].copy()
    summary["seeds"] = grouped.size()
    summary["max_extra_delay_limit"] = MAX_EXTRA_DELAY_MINUTES
    for metric in SUMMARY_METRICS:
        summary[f"{metric}_mean"] = grouped[metric].mean()
        summary[f"{metric}_std"] = grouped[metric].std(ddof=0)
    return summary.reset_index()


def feature_label(row):
    """Short label of the features a configuration switches on."""
    on = [name for name, active in (
        ("bus", bool(row["buses"])),
        ("walk", bool(row["walk_radius"])),
        ("cong", row["congestion"] != "off"),
        ("pat", not pd.isna(row["patience_max"]) and bool(row["patience_max"])),
    ) if active]
    if len(on) == 4:
        return "all 4"
    return "+" + "+".join(on) if on else ""


def bar_chart(ax, summary, metric):
    """One bar per configuration, coloured/hatched by sharing mode; the tick
    label shows the config id and, below it, the features switched on."""
    x = range(len(summary))
    for i, (_, row) in enumerate(summary.iterrows()):
        color, hatch = MODE_STYLE[row["sharing_mode"]]
        ax.bar(i, row[f"{metric}_mean"], yerr=row[f"{metric}_std"], color=color,
               hatch=hatch, edgecolor="white", linewidth=0.8, width=0.75,
               error_kw={"elinewidth": 1, "capsize": 2, "ecolor": "#52514e"})
    labels = [f"{row['config_id']}\n{feature_label(row)}"
              for _, row in summary.iterrows()]
    ax.set_xticks(list(x), labels)
    ax.set_xlim(-0.6, len(summary) - 0.4)
    ax.set_title(SUMMARY_METRICS[metric], fontsize=10, color="#0b0b0b")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#b5b4ae")
    ax.tick_params(colors="#52514e", labelsize=7.5)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.6)
    ax.set_axisbelow(True)


def legend_handles():
    from matplotlib.patches import Patch

    return [Patch(facecolor=c, hatch=h, edgecolor="white", label=f"sharing: {m}")
            for m, (c, h) in MODE_STYLE.items()]


def make_charts(summary, out_dir):
    charts = out_dir / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    note = ("Bars: mean over seeds; error bars: standard deviation. Under each id: "
            "features on (bus = buses, walk = walking, cong = congestion, "
            "pat = patience).")
    for metric in CHART_METRICS:
        fig, ax = plt.subplots(figsize=(10, 4))
        bar_chart(ax, summary, metric)
        ax.legend(handles=legend_handles(), fontsize=8, frameon=False,
                  loc="upper left", bbox_to_anchor=(1.0, 1.0))
        fig.text(0.01, 0.01, note, fontsize=7, color="#52514e")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(charts / f"{metric}.png", dpi=150)
        plt.close(fig)

    fig, axes = plt.subplots(2, 4, figsize=(24, 9.5))
    for ax, metric in zip(axes.flat, CHART_METRICS):
        bar_chart(ax, summary, metric)
    fig.legend(handles=legend_handles(), loc="upper center", ncol=3,
               frameon=False, fontsize=10)
    fig.text(0.01, 0.01, note + f" Max extra delay fixed at "
             f"{MAX_EXTRA_DELAY_MINUTES} min.", fontsize=9, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95), h_pad=2.5, w_pad=2)
    fig.savefig(charts / "comparison.png", dpi=150)
    plt.close(fig)


def run(config_path="experiments.csv", seeds=SEEDS, out="results",
        only=None, charts=True):
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    configs = load_configs(config_path, only)
    frames = []
    for _, row in configs.iterrows():
        print(f"Running {row['config_id']}: {row['description']} ...", flush=True)
        frames.append(run_config(row, list(seeds)))
    runs, passengers = split_records(pd.concat(frames, ignore_index=True))
    summary = summarise(runs, configs)

    runs.to_csv(out_dir / "runs.csv", index=False)
    passengers.to_csv(out_dir / "passengers.csv", index=False)
    summary.to_csv(out_dir / "summary.csv", index=False)
    if charts:
        make_charts(summary, out_dir)
    return runs, passengers, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config", default="experiments.csv")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    parser.add_argument("--out", default="results")
    parser.add_argument("--only", nargs="+", help="config_id values to run")
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args()

    _, _, summary = run(args.config, args.seeds, args.out, args.only,
                        not args.no_charts)
    table = summary[["config_id", "sharing_mode", "capacity"]].copy()
    table["features"] = [feature_label(row) or "-" for _, row in summary.iterrows()]
    for metric in CHART_METRICS:
        table[metric] = summary[f"{metric}_mean"]
    print(table.to_string(index=False, float_format="{:.1f}".format))
    print(f"\nResults written to {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
