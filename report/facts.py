"""Print every number used in the report, straight from the result CSVs.

Run from the project folder: python report/facts.py
All values are mean ± std over seeds (std with ddof=0, as in summary.csv).
"""

import pandas as pd

S = pd.read_csv("results/summary.csv").set_index("config_id")
RUNS = pd.read_csv("results/runs.csv")
SWEEP = pd.read_csv("results_sweep/summary.csv").set_index("config_id")
FLEET = pd.read_csv("results_fleet/summary.csv").set_index("config_id")
EQUIV = pd.read_csv("results_analysis/fleet_equivalence.csv")


def pm(frame, idx, metric, digits=1):
    return (f"{frame.loc[idx, metric + '_mean']:.{digits}f} ± "
            f"{frame.loc[idx, metric + '_std']:.{digits}f}")


def per_run(runs, column):
    """mean ± std over seeds of a per-run column, per config."""
    g = runs.groupby("config_id", sort=False)[column]
    return {k: f"{m:.1f} ± {s:.1f}" for k, m, s in
            zip(g.mean().index, g.mean(), g.std(ddof=0))}


print("== S1-S12 ==")
cols = ["completed_pct", "avg_wait_completed", "avg_in_vehicle_completed",
        "avg_total_completed", "avg_extra_delay_completed", "distance_per_completed",
        "empty_distance_pct", "bus_share_pct", "acceptable_pct", "abandoned_pct",
        "shared_completed", "max_extra_delay"]
for i in S.index:
    print(i, " | ".join(f"{c}={pm(S, i, c)}" for c in cols))

print("\n== per mode (S6, S7, S12) ==")
for i in ["S6", "S7", "S12"]:
    print(i, " | ".join(f"{c}={pm(S, i, c)}" for c in [
        "completed_pct_taxi", "completed_pct_bus", "avg_wait_completed_taxi",
        "avg_wait_completed_bus", "avg_total_completed_taxi",
        "avg_total_completed_bus"]), "| occupancy", pm(S, i, "avg_bus_occupancy", 2))

runs = RUNS.assign(vehicle=RUNS.total_distance + RUNS.bus_distance,
                   msg_per_completed=RUNS.messages / RUNS.completed)
runs = runs.assign(vehicle_per_completed=runs.vehicle / runs.completed)
print("\n== vehicle distance (taxi + bus) per scenario ==")
for name in ["total_distance", "bus_distance", "vehicle", "vehicle_per_completed"]:
    print(name, per_run(runs, name))
print("\n== messages ==")
print("messages per run", per_run(runs, "messages"))
print("messages per completed passenger", per_run(runs, "msg_per_completed"))
print("max extra delay over all runs:", RUNS.max_extra_delay.max())

print("\n== sweep ==")
for i in SWEEP.index:
    print(i, " | ".join(f"{c}={pm(SWEEP, i, c)}" for c in [
        "completed_pct", "avg_wait_completed", "avg_in_vehicle_completed",
        "avg_total_completed", "avg_extra_delay_completed", "distance_per_completed",
        "empty_distance_pct"]))

print("\n== fleet equivalence ==")
pd.set_option("display.width", 250)
cols = ["mode", "target", "num_taxis", "completed_pct", "total_distance",
        "bus_distance", "vehicle_distance", "empty_distance_pct"]
for _, r in EQUIV.iterrows():
    if pd.isna(r["num_taxis"]):
        print(r["mode"], r["target"], "not reached")
        continue
    print(r["mode"], "|", r["target"], "|", int(r["num_taxis"]), "|",
          " | ".join(f"{m}={r[m + '_mean']:.1f} ± {r[m + '_std']:.1f}"
                     for m in cols[3:]))
print("none 30 taxis:", pm(FLEET, "F_none1_T30", "completed_pct"),
      pm(FLEET, "F_none1_T30", "total_distance"))
