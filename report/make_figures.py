"""Draw the report figures into report/figures/.

Run from the project folder: python report/make_figures.py

- sequence.png, taxi_states.png: the two protocol / state diagrams;
- map_S12.png, comparison.png, sweep.png, fleet.png: print-sized versions of
  docs/map_S12.png, results/charts/comparison.png and results_analysis/
  sweep.png / fleet.png, drawn by the same project code from the same data
  (results/, results_sweep/, results_fleet/) at the width of an A4 page, so
  their text stays readable when printed. Nothing in results/ is changed.
"""

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, ".")  # project modules (run from the project folder)
sys.path.insert(0, "report")  # sequence_logs.py

OUT = Path("report/figures")
INK = "#222222"
MUTED = "#666666"


def sequence_diagram():
    """One auction round (one simulated minute): passenger, taxi A, taxi B."""
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.4)
    ax.axis("off")
    lanes = {"Passenger P": 2.6, "Taxi A": 5.8, "Taxi B": 8.8}
    for name, x in lanes.items():
        ax.add_patch(FancyBboxPatch((x - 0.9, 9.45), 1.8, 0.7,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    facecolor="#eef2f7", edgecolor=INK, linewidth=0.8))
        ax.text(x, 9.8, name, ha="center", va="center", fontsize=9, fontweight="bold")
        ax.plot([x, x], [0.4, 9.45], color="#999999", linewidth=0.9, linestyle="--")
    P, A, B = lanes.values()

    def msg(y, x0, x1, label, dashed=False, color=INK):
        ax.annotate("", xy=(x1, y), xytext=(x0, y),
                    arrowprops={"arrowstyle": "-|>", "color": color, "linewidth": 1.1,
                                "linestyle": "--" if dashed else "-",
                                "shrinkA": 2, "shrinkB": 2})
        ax.text((x0 + x1) / 2, y + 0.12, label, ha="center", va="bottom",
                fontsize=7.6, color=color)

    phases = [(8.6, "1"), (7.0, "2"), (5.4, "3"), (4.0, "4"), (2.2, "5")]
    for y, number in phases:
        ax.text(0.15, y, f"phase {number}", fontsize=7.5, color=MUTED, va="center")
    msg(8.85, P, A, "REQUEST (origin, destination)")
    msg(8.25, P, B, "REQUEST (origin, destination)")
    msg(7.3, A, P, "PROPOSE (can_accept, eta = 4 min)")
    msg(6.7, B, P, "PROPOSE (can_accept, eta = 7 min)")
    ax.text(P + 0.15, 5.95, "picks the lowest eta (ties: lowest taxi id)",
            fontsize=7.3, color=MUTED, style="italic")
    msg(5.4, P, A, "ACCEPT")
    ax.text(A + 0.2, 5.25, "taxi A re-checks the plan\n(it may have accepted\n"
            "someone else this minute)",
            fontsize=7.3, color=MUTED, style="italic", va="top")
    msg(3.75, A, P, "CONFIRM (promised pickup, pickup district)")
    msg(3.05, A, P, "or REJECT: P asks again next minute", dashed=True, color=MUTED)
    ax.text(P + 0.2, 2.2, "P reads the reply: CONFIRM makes it assigned;\n"
            "taxi A has added P's pickup and drop-off to its stops",
            fontsize=7.3, color=MUTED, style="italic", va="center")
    ax.text(5.0, 0.05, "All messages go through TaxiModel.send() into the receiver's "
            "inbox; the whole round happens within one step (one minute).",
            ha="center", fontsize=7.3, color=MUTED)
    fig.tight_layout()
    fig.savefig(OUT / "sequence.png", dpi=200)
    plt.close(fig)


def state_diagram():
    """Taxi states (agents.TaxiAgent.update_state / serve_stops)."""
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    colors = {"idle": "#9e9e9e", "to_pickup": "#ff9800", "picking_up": "#43a047",
              "travelling": "#1e88e5", "dropping_off": "#8e24aa"}
    pos = {"idle": (1.3, 3.0), "to_pickup": (4.0, 5.0), "picking_up": (8.4, 5.0),
           "travelling": (8.4, 1.0), "dropping_off": (4.0, 1.0)}
    notes = {"idle": "no planned stop", "to_pickup": "driving to the next pickup",
             "picking_up": "standing, 1 min boarding",
             "travelling": "driving to the next drop-off",
             "dropping_off": "standing, 1 min alighting"}
    w, h = 2.3, 0.95
    for name, (x, y) in pos.items():
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.2",
                                    facecolor=colors[name], edgecolor=INK,
                                    linewidth=0.9, alpha=0.9))
        ax.text(x, y + 0.13, name, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color="white")
        ax.text(x, y - 0.22, notes[name], ha="center", va="center", fontsize=6.6,
                color="white")

    def edge(a, b, label, rad=0.0, lx=0.0, ly=0.0, start=None, end=None):
        (x0, y0), (x1, y1) = start or pos[a], end or pos[b]
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                     connectionstyle=f"arc3,rad={rad}",
                                     arrowstyle="-|>", mutation_scale=11,
                                     color=INK, linewidth=1.0,
                                     shrinkA=22, shrinkB=22))
        ax.text((x0 + x1) / 2 + lx, (y0 + y1) / 2 + ly, label, ha="center",
                va="center", fontsize=7, color=INK,
                bbox={"boxstyle": "round,pad=0.15", "facecolor": "white",
                      "edgecolor": "none", "alpha": 0.9})

    # Straight arrows are labelled on the inner side, curved ones on the outer.
    edge("idle", "to_pickup", "CONFIRM:\nnew stops", lx=-0.75, ly=0.2)
    edge("to_pickup", "picking_up", "reaches the pickup district", ly=-0.32)
    edge("picking_up", "travelling", "next stop is\na drop-off", lx=0.65)
    edge("picking_up", "to_pickup", "next stop is another pickup", rad=0.35,
         ly=0.78)
    edge("travelling", "dropping_off", "reaches the destination", ly=0.32)
    edge("dropping_off", "idle", "no stop left", lx=-0.6, ly=-0.2)
    edge("dropping_off", "to_pickup", "next stop\nis a pickup", lx=-0.6)
    edge("dropping_off", "travelling", "next stop is another drop-off", rad=0.35,
         ly=-0.78)
    fig.tight_layout()
    fig.savefig(OUT / "taxi_states.png", dpi=200)
    plt.close(fig)


PAGE_WIDTH = 7.0  # inches: the 17 cm text width of an A4 page with 2 cm margins

# --- Sequence diagrams drawn from report/sequence_logs.py ------------------
MSG_COLORS = {"CONFIRM": "#1b7f3b", "REJECT": "#c62828"}


def message_label(m, origin, compact):
    """Arrow label: message type and its key data."""
    data, kind = m["data"], m["type"]
    at = ""
    district = data.get("pickup_district")
    if district is not None and list(district) != list(origin):
        at = f" at ({district[0]},{district[1]})"
    if kind == "REQUEST":
        if compact:
            return "REQUEST"
        o, d = data["origin"], data["destination"]
        return f"REQUEST ({o[0]},{o[1]})→({d[0]},{d[1]})"
    if kind == "PROPOSE":
        if not data["can_accept"]:
            return "PROPOSE: cannot accept"
        return f"PROPOSE eta {data['eta']}{'' if compact else ' min'}{at}"
    if kind == "CONFIRM":
        return f"CONFIRM pickup min {data['pickup_time']}{at}"
    return kind


def shorten(text):
    """Compact event note: drop the coordinates of boarding / arrival."""
    return re.sub(r" at \(\d+, \d+\)", "", text)


def sequence_rows(log):
    """Rows to draw, in time order: messages grouped by minute (identical
    consecutive minutes collapsed into one note) with the events merged in."""
    by_minute = {}
    for m in log["messages"]:
        by_minute.setdefault(m["minute"], []).append(m)
    request_minute = {}
    for m in log["messages"]:
        if m["type"] == "REQUEST":
            request_minute.setdefault(m["sender"], m["minute"])

    def signature(msgs):
        return [(m["sender"], m["receiver"], m["type"], json.dumps(m["data"]))
                for m in msgs]

    rows, previous, skipped = [], None, []
    events = list(log["events"])

    def flush_events(up_to):
        while events and events[0]["minute"] <= up_to:
            rows.append(("event", events.pop(0)))

    def flush_skipped():
        if skipped:
            rows.append(("repeat", (skipped[0], skipped[-1])))
            skipped.clear()

    for minute in sorted(by_minute):
        msgs = by_minute[minute]
        if previous is not None and signature(msgs) == previous:
            skipped.append(minute)
            continue
        flush_skipped()
        flush_events(minute - 1)
        rows.append(("minute", minute))
        for m in msgs:
            rows.append(("message", m))
        # Patience: a proposal that came too late gets no ACCEPT.
        for m in msgs:
            patience = log["patience"].get(str(m["receiver"]))
            accepted = any(a["type"] == "ACCEPT" and a["sender"] == m["receiver"]
                           for a in msgs)
            if (m["type"] == "PROPOSE" and m["data"]["can_accept"] and patience
                    and not accepted):
                deadline = request_minute[m["receiver"]] + patience
                rows.append(("note", (m["receiver"],
                                      f"pickup at min {minute + m['data']['eta']} > "
                                      f"patience end {deadline}: no ACCEPT")))
        previous = signature(msgs)
    flush_skipped()
    flush_events(10 ** 6)
    return rows


def draw_sequence(ax, log, compact=False):
    """Draw one scenario log as a sequence diagram into `ax`."""
    fs = 6.3 if compact else 7.6
    lanes = {lane["id"]: lane["label"] for lane in log["lanes"]}
    ids = list(lanes)
    left, right = (1.35, 9.8)
    xs = {uid: left + (right - left) * (i + 0.5) / len(ids) for i, uid in enumerate(ids)}
    rows = sequence_rows(log)
    n = len(rows) + (1 if log["note"] else 0)
    ax.set_xlim(0, 10)
    ax.set_ylim(n + 0.6, -1.6)
    ax.axis("off")
    ax.set_title(log["title"], fontsize=fs + 1.5, loc="left", pad=2)
    for uid, x in xs.items():
        ax.text(x, -0.9, lanes[uid], ha="center", va="center", fontsize=fs,
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "#eef2f7",
                      "edgecolor": INK, "linewidth": 0.7})
        ax.plot([x, x], [-0.5, n + 0.4], color="#aaaaaa", linewidth=0.8,
                linestyle="--", zorder=0)
    vehicle = next((uid for uid, label in lanes.items()
                    if label.startswith(("Taxi", "Bus"))), None)

    def note(x, y, text, ha="center", color=MUTED):
        ax.text(x, y, text, ha=ha, va="center", fontsize=fs - 0.4, color=color,
                style="italic", zorder=3,
                bbox={"boxstyle": "round,pad=0.15", "facecolor": "white",
                      "edgecolor": "none", "alpha": 0.9})

    def lane_note(uid, y, text):
        x = xs[uid]
        # Outer lanes: the note starts / ends just inside, clear of the lifeline.
        if x == min(xs.values()):
            note(x + 0.12, y, text, ha="left")
        elif x == max(xs.values()):
            note(x - 0.12, y, text, ha="right")
        else:
            note(x, y, text)

    for y, (kind, item) in enumerate(rows):
        if kind == "minute":
            ax.text(0.05, y + 0.05, f"min {item}", fontsize=fs, color=MUTED,
                    va="center", fontweight="bold")
            ax.plot([0.05, 9.95], [y - 0.45, y - 0.45], color="#e3e3e3",
                    linewidth=0.6, zorder=0)
        elif kind == "message":
            x0, x1 = xs[item["sender"]], xs[item["receiver"]]
            refused = item["type"] == "PROPOSE" and not item["data"]["can_accept"]
            color = MUTED if refused else MSG_COLORS.get(item["type"], INK)
            ax.annotate("", xy=(x1, y + 0.12), xytext=(x0, y + 0.12),
                        arrowprops={"arrowstyle": "-|>", "color": color,
                                    "linewidth": 1.0, "shrinkA": 1, "shrinkB": 1,
                                    "linestyle": "--" if refused else "-"})
            passenger = next(str(uid) for uid in (item["sender"], item["receiver"])
                             if str(uid) in log["origins"])
            origin = log["origins"][passenger]
            ax.text((x0 + x1) / 2, y - 0.05, message_label(item, origin, compact),
                    ha="center", va="bottom", fontsize=fs, color=color, zorder=2,
                    bbox={"boxstyle": "square,pad=0.05", "facecolor": "white",
                          "edgecolor": "none"})
        elif kind == "repeat":
            a, b = item
            span = f"minute {a}" if a == b else f"minutes {a}-{b}"
            note(5.4, y, f"{span}: the same exchange again")
        elif kind == "note":
            uid, text = item
            lane_note(uid, y, text)
        elif kind == "event":
            text = f"{item['text']} (min {item['minute']})"
            if compact:
                text = shorten(text)
            if vehicle is not None and item["text"].startswith(("boards", "leaves")):
                ax.plot([xs[item["agent"]], xs[vehicle]], [y, y], color="#7a7a7a",
                        linewidth=1.0, linestyle=":", zorder=1)
                note((xs[item["agent"]] + xs[vehicle]) / 2, y, text, color=INK)
            else:
                lane_note(item["agent"], y, text)
    if log["note"]:
        note(5.4, len(rows), log["note"], color=INK)
    return len(rows)


def sequence_figures():
    """docs/sequence_<scenario>.png (one per scenario) and the report panel
    report/figures/negotiation.png with scenarios a-d."""
    import sequence_logs

    logs = sequence_logs.all_logs()
    for log in logs:
        rows = len(sequence_rows(log)) + (1 if log["note"] else 0)
        fig, ax = plt.subplots(figsize=(7.2, 0.95 + 0.27 * rows))
        draw_sequence(ax, log)
        fig.tight_layout(pad=0.4)
        fig.savefig(Path("docs") / f"sequence_{log['name']}.png", dpi=200)
        plt.close(fig)
    # Row heights proportional to the content, so every panel has the same
    # spacing between messages.
    sizes = [len(sequence_rows(log)) + 2.2 for log in logs[:4]]
    ratios = [max(sizes[0], sizes[1]), max(sizes[2], sizes[3])]
    fig, axes = plt.subplots(2, 2, figsize=(PAGE_WIDTH, 0.19 * sum(ratios) + 0.4),
                             gridspec_kw={"height_ratios": ratios})
    for ax, log in zip(axes.flat, logs[:4]):
        draw_sequence(ax, log, compact=True)
    for row in range(2):  # same y scale inside a row
        top = max(axes[row, 0].get_ylim()[0], axes[row, 1].get_ylim()[0])
        for ax in axes[row]:
            ax.set_ylim(top, -1.6)
    fig.tight_layout(pad=0.5, h_pad=1.0, w_pad=0.6)
    fig.savefig(OUT / "negotiation.png", dpi=220)
    plt.close(fig)


def map_figure():
    """The S12 map at minute 40, seed 1 (as docs/map_S12.png), page-sized."""
    import app
    import run_experiments as rx
    from model import TaxiModel

    row = rx.load_configs("experiments.csv", ["S12"]).iloc[0]
    params = {c: row[c] for c in rx.PARAM_COLUMNS}
    params = {k: (v.item() if hasattr(v, "item") else v) for k, v in params.items()}
    params = {k: (None if pd.isna(v) else v) for k, v in params.items()}
    m = TaxiModel(seed=1, **params)
    while m.minute < 40:
        m.step()
    fig = app.draw_city(m, Figure(figsize=(PAGE_WIDTH, 6.3), layout="constrained"))
    fig.savefig(OUT / "map_S12.png", dpi=220, bbox_inches="tight", pad_inches=0.05)


def comparison_figure():
    """results/charts/comparison.png in a 4 x 2 layout for the page width."""
    import run_experiments as rx

    summary = pd.read_csv("results/summary.csv")
    fig, axes = plt.subplots(4, 2, figsize=(PAGE_WIDTH, 7.0))
    for ax, metric in zip(axes.flat, rx.CHART_METRICS):
        rx.bar_chart(ax, summary, metric)
        ax.title.set_fontsize(8.5)
        ax.tick_params(axis="x", labelsize=5.5)
        ax.tick_params(axis="y", labelsize=7)
    fig.legend(handles=rx.legend_handles(), loc="upper center", ncol=3,
               frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.975), h_pad=0.8)
    fig.savefig(OUT / "comparison.png", dpi=220)
    plt.close(fig)


def analysis_figures():
    """results_analysis/sweep.png and fleet.png, page-sized."""
    import plot_analysis as pa

    sweep = pd.read_csv("results_sweep/summary.csv")
    fleet = pa.with_vehicle_distance(pd.read_csv("results_fleet/summary.csv"),
                                     pd.read_csv("results_fleet/runs.csv"))
    pa.plot_sweep(sweep, path=OUT / "sweep.png", figsize=(PAGE_WIDTH, 6.9),
                  grid=(3, 2), compact=True, dpi=220)
    pa.plot_fleet(fleet, pa.s1_level(), path=OUT / "fleet.png",
                  figsize=(PAGE_WIDTH, 3.6), compact=True, dpi=220)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    sequence_diagram()
    state_diagram()
    map_figure()
    comparison_figure()
    analysis_figures()
    sequence_figures()
    print("written", sorted(p.name for p in OUT.iterdir()),
          sorted(p.name for p in Path("docs").glob("sequence_*.png")))
