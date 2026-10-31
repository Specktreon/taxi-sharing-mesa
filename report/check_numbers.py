"""Check every number in report/report.md against the result CSVs.

Run from the project folder: python report/check_numbers.py
1. Every "a ± b" in the report must be a mean ± std (1 or 2 decimals) that the
   CSVs produce: summary columns, fleet_equivalence.csv, or per-run derived
   values (vehicle distance, messages, per completed passenger).
2. Derived numbers quoted without ± are recomputed and asserted below.
Exits with an error listing any number that does not match.
"""

import re
import subprocess
import sys

import pandas as pd

TEXT = open("report/report.md", encoding="utf-8").read()
allowed = set()


def add(mean, std):
    for d in (1, 2):
        allowed.add(f"{mean:.{d}f} ± {std:.{d}f}")


for path in ["results/summary.csv", "results_sweep/summary.csv",
             "results_fleet/summary.csv", "results_analysis/fleet_equivalence.csv"]:
    frame = pd.read_csv(path)
    for col in frame.columns:
        if col.endswith("_mean") and col[:-5] + "_std" in frame.columns:
            for m, s in zip(frame[col], frame[col[:-5] + "_std"]):
                if pd.notna(m) and pd.notna(s):
                    add(m, s)

for path in ["results/runs.csv", "results_fleet/runs.csv"]:
    runs = pd.read_csv(path)
    runs = runs.assign(vehicle=runs.total_distance + runs.bus_distance)
    runs = runs.assign(vehicle_per_completed=runs.vehicle / runs.completed,
                       messages_per_completed=runs.messages / runs.completed)
    for col in ["vehicle", "vehicle_per_completed", "messages",
                "messages_per_completed"]:
        g = runs.groupby("config_id")[col]
        for m, s in zip(g.mean(), g.std(ddof=0)):
            add(m, s)

found = re.findall(r"(\d+(?:\.\d+)?) ± (\d+(?:\.\d+)?)", TEXT)
bad = sorted({f"{m} ± {s}" for m, s in found} - allowed)
print(f"{len(found)} mean ± std values in the report, {len(set(found))} distinct")

# Derived numbers quoted without ± (recomputed from the CSVs).
S = pd.read_csv("results/summary.csv").set_index("config_id")
E = pd.read_csv("results_analysis/fleet_equivalence.csv")
R = pd.read_csv("results/runs.csv")


def equiv(mode, target):
    row = E[(E["mode"] == mode) & (E["target"] == target)].iloc[0]
    return row


none_s1 = equiv("single rides (none, cap 1)", "S1 level")
det_s1 = equiv("detour sharing, cap 4", "S1 level")
saving = 100 * (1 - det_s1["total_distance_mean"] / none_s1["total_distance_mean"])
fewer = 100 * (1 - det_s1["num_taxis"] / none_s1["num_taxis"])
checks = {
    "41.0 % less driving": f"{saving:.1f}" == "41.0",
    "40 % fewer taxis (12 vs 20)": (int(det_s1["num_taxis"]), int(none_s1["num_taxis"]),
                                    round(fewer)) == (12, 20, 40),
    "41 % less driving (conclusion)": round(saving) == 41,
    "10 taxis with buses for the S1 level": int(
        equiv("detour sharing, cap 4 + buses", "S1 level")["num_taxis"]) == 10,
    "20 and 18 taxis for 85 %": (
        int(equiv("detour sharing, cap 4", "85 %")["num_taxis"]),
        int(equiv("detour sharing, cap 4 + buses", "85 %")["num_taxis"])) == (20, 18),
    "single rides never reach 85 %": pd.isna(
        equiv("single rides (none, cap 1)", "85 %")["num_taxis"]),
    "S4 messages = 90 x (20 + 20 + 1 + 1) = 3780 in every run": (
        (R.loc[R.config_id == "S4", "messages"] == 90 * (20 + 20 + 1 + 1)).all()),
    "largest extra delay ever = 10": R["max_extra_delay"].max() == 10,
    "trips of 1 to 58 districts on 30x30": (1, 29 + 29) == (1, 58),
}
tests = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                       capture_output=True, text=True).stdout
n_tests = int(re.search(r"(\d+) tests? collected", tests).group(1))
checks[f"149 pytest tests (collected: {n_tests})"] = n_tests == 149

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("ok   " if ok else "FAIL ") + name)
if bad:
    print("NOT FOUND in the CSVs:", bad)
if bad or failed:
    sys.exit(1)
print("all numbers verified")
