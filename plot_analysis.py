"""Line charts and the fleet-equivalence table for the analysis experiments.

Usage (after running the two experiment sets):
    python run_experiments.py --config experiments_sweep.csv --out results_sweep --no-charts
    python run_experiments.py --config experiments_fleet.csv --out results_fleet --no-charts
    python plot_analysis.py

Reads results_sweep/summary.csv, results_fleet/summary.csv and runs.csv, and
(for the S1 reference level) results/summary.csv. Writes to results_analysis/:
    sweep.png              load sweep (x = passengers), mean line + std band
    fleet.png              fleet sizes (x = taxis), with S1 and 85 % lines; the
                           distance panel adds taxi + bus distance (dashed)
    fleet_equivalence.csv  per mode: smallest fleet reaching the S1 level / 85 %,
                           with taxi, bus and total vehicle distance

Vehicle distance = taxi distance + bus distance, summed per run before taking
mean and std. Buses drive their full lines whatever their load, so with buses
on, the total vehicle distance is much larger than the taxi distance. A bus
district is not equivalent to a car district (bigger vehicle), so the total is
a count of vehicle movements, not a pollution measure.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from run_experiments import SUMMARY_METRICS

OUT = Path("results_analysis")
TARGET_PCT = 85.0

# One line per mode: (label, colour, line style).
MODES = {
    ("none", 1, False): ("single rides (none, cap 1)", "#2a78d6", "-"),
    ("detour", 2, False): ("detour sharing, cap 2", "#1baf7a", "--"),
    ("detour", 4, False): ("detour sharing, cap 4", "#0b6e4f", "-"),
    ("detour", 4, True): ("detour sharing, cap 4 + buses", "#d81b60", "-"),
}
SWEEP_METRICS = ["completed_pct", "avg_wait_completed", "avg_total_completed",
                 "avg_extra_delay_completed", "distance_per_completed",
                 "empty_distance_pct"]


def mode_key(row):
    return (row["sharing_mode"], int(row["capacity"]), bool(row["buses"]))


def by_mode(summary, x):
    """{mode key: rows sorted by x}."""
    summary = summary.assign(_mode=[mode_key(r) for _, r in summary.iterrows()])
    return {key: group.sort_values(x) for key, group in summary.groupby("_mode",
                                                                        sort=False)}


def line_panel(ax, groups, x, metric, xlabel):
    for key, rows in groups.items():
        label, color, style = MODES[key]
        mean, std = rows[f"{metric}_mean"], rows[f"{metric}_std"]
        ax.plot(rows[x], mean, style, color=color, linewidth=1.8, marker="o",
                markersize=3.5, label=label)
        ax.fill_between(rows[x], mean - std, mean + std, color=color, alpha=0.15,
                        linewidth=0)
    ax.set_title(SUMMARY_METRICS[metric], fontsize=10)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(color="#e6e5e0", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def with_vehicle_distance(summary, runs):
    """Add vehicle_distance (taxi + bus per run) and vehicle distance per
    completed passenger, mean and std (ddof=0, as in summary.csv)."""
    runs = runs.assign(vehicle_distance=runs["total_distance"] + runs["bus_distance"])
    runs = runs.assign(vehicle_distance_per_completed=(runs["vehicle_distance"]
                                                       / runs["completed"]))
    grouped = runs.groupby("config_id", sort=False)
    stats = pd.DataFrame(index=grouped.size().index)
    for metric in ("vehicle_distance", "vehicle_distance_per_completed"):
        stats[f"{metric}_mean"] = grouped[metric].mean()
        stats[f"{metric}_std"] = grouped[metric].std(ddof=0)
    return summary.merge(stats, left_on="config_id", right_index=True)


def s1_level():
    s = pd.read_csv("results/summary.csv").set_index("config_id")
    return s.loc["S1", "completed_pct_mean"]


def compact_layout(fig, axes):
    """Narrow (print) layout: wrapped panel titles, one legend above the panels."""
    for ax in axes.flat:
        ax.set_title(textwrap.fill(ax.get_title(), 34), fontsize=9)
        if ax.get_legend():
            ax.get_legend().remove()
    handles, labels = [], []
    for ax in axes.flat:  # unique entries, in drawing order
        for h, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(h)
                labels.append(label)
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=8)


def plot_sweep(sweep, path=OUT / "sweep.png", figsize=(15, 8.5), grid=(2, 3),
               compact=False, dpi=150):
    """Load sweep panels. compact=True draws the narrow print version of the
    same chart (no suptitle, wrapped titles, legend above the panels)."""
    groups = by_mode(sweep, "num_passengers")
    fig, axes = plt.subplots(*grid, figsize=figsize)
    for ax, metric in zip(axes.flat, SWEEP_METRICS):
        line_panel(ax, groups, "num_passengers", metric, "passengers (20 taxis)")
    axes.flat[0].legend(fontsize=8, frameon=False)
    if compact:
        compact_layout(fig, axes)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
    else:
        fig.suptitle("Load sweep on the 30x30 base: 20 taxis, 30-180 passengers "
                     "(lines: mean over seeds 1-10; bands: ± 1 std)", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def plot_fleet(fleet, reference, path=OUT / "fleet.png", figsize=(13, 4.8),
               compact=False, dpi=150):
    groups = by_mode(fleet, "num_taxis")
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    line_panel(axes[0], groups, "num_taxis", "completed_pct", "taxis (90 passengers)")
    for level, text in ((reference, f"S1 (none, 20 taxis): {reference:.1f} %"),
                        (TARGET_PCT, f"{TARGET_PCT:.0f} %")):
        axes[0].axhline(level, color="#52514e", linewidth=0.9, linestyle=":")
        axes[0].text(axes[0].get_xlim()[1], level, f" {text}", fontsize=7.5,
                     va="bottom", ha="right", color="#52514e")
    line_panel(axes[1], groups, "num_taxis", "total_distance", "taxis (90 passengers)")
    # With buses, also the distance driven by all vehicles (taxis + buses).
    bus_rows = groups[("detour", 4, True)]
    mean = bus_rows["vehicle_distance_mean"]
    std = bus_rows["vehicle_distance_std"]
    color = MODES[("detour", 4, True)][1]
    axes[1].plot(bus_rows["num_taxis"], mean, "--", color=color, linewidth=1.8,
                 marker="s", markersize=3.5,
                 label="detour cap 4 + buses: taxi + bus distance")
    axes[1].fill_between(bus_rows["num_taxis"], mean - std, mean + std, color=color,
                         alpha=0.10, linewidth=0)
    axes[1].set_title("Vehicle distance (districts): taxis; dashed = taxis + buses",
                      fontsize=10)
    axes[1].legend(fontsize=8, frameon=False, loc="lower right")
    axes[0].legend(fontsize=8, frameon=False, loc="lower right")
    if compact:
        axes[1].set_title("Distance driven (districts)")
        compact_layout(fig, axes)
        fig.tight_layout(rect=(0, 0, 1, 0.87))
    else:
        fig.suptitle("Fleet size for the same service (90 passengers; mean over "
                     "seeds 1-10, bands ± 1 std)", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def fleet_equivalence(fleet, reference):
    """Per mode, the smallest fleet whose mean completed % reaches the S1 level
    and TARGET_PCT, with its taxi distance and empty share."""
    rows = []
    for key, group in by_mode(fleet, "num_taxis").items():
        for target_name, level in (("S1 level", reference), ("85 %", TARGET_PCT)):
            hit = group[group["completed_pct_mean"] >= level]
            row = {"mode": MODES[key][0], "target": target_name,
                   "target_pct": round(level, 1)}
            if hit.empty:
                row["num_taxis"] = None
            else:
                best = hit.iloc[0]
                row["num_taxis"] = int(best["num_taxis"])
                for metric in ("completed_pct", "total_distance", "bus_distance",
                               "vehicle_distance", "empty_distance_pct",
                               "distance_per_completed",
                               "vehicle_distance_per_completed"):
                    row[f"{metric}_mean"] = best[f"{metric}_mean"]
                    row[f"{metric}_std"] = best[f"{metric}_std"]
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    sweep = pd.read_csv("results_sweep/summary.csv")
    fleet = with_vehicle_distance(pd.read_csv("results_fleet/summary.csv"),
                                  pd.read_csv("results_fleet/runs.csv"))
    reference = s1_level()
    plot_sweep(sweep)
    plot_fleet(fleet, reference)
    table = fleet_equivalence(fleet, reference)
    table.to_csv(OUT / "fleet_equivalence.csv", index=False)
    pd.set_option("display.width", 200)
    print(table.round(1).to_string(index=False))
    print(f"\nCharts and table written to {OUT.resolve()}")


if __name__ == "__main__":
    main()
