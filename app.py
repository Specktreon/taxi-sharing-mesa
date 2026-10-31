"""Interactive Mesa (Solara) visualization.

Run from the project folder:
    python -m solara run app.py
then open the printed URL (default http://localhost:8765).
Use the sidebar to change parameters, then Reset / Step / Play.
"""

import math
from collections import Counter

import numpy as np
import solara
from matplotlib import patheffects
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from mesa.visualization import SolaraViz

from agents import (ABANDONED, ASSIGNED, NOT_COMPLETED, PICKUP, WAITING,
                    stop_district)
from config import (ARRIVAL_MODES, BOARDING_MINUTES, CAPACITIES, CENTER_FACTOR,
                    CONGESTION_CENTER_SIZE, CONGESTION_MODES, DEFAULTS,
                    MAX_EXTRA_DELAY_MINUTES, PATIENCE_MIN, RING_FACTOR,
                    SHARING_MODES)
from model import TaxiModel
from routing import congestion_center

# One consistent legend for the grid.
TAXI_COLORS = {
    "idle": "#9e9e9e",
    "to_pickup": "#ff9800",
    "travelling": "#1e88e5",
    "picking_up": "#43a047",
    "dropping_off": "#8e24aa",
}
WAITING_COLOR = "#e53935"  # red: no taxi yet
ASSIGNED_COLOR = "#fdd835"  # yellow: a taxi is on its way
ABANDONED_COLOR = "#8d6e63"  # brown ring: gave up waiting
RING_SHADE = "#fff1dc"  # congestion ring (light)
CENTER_SHADE = "#fde0b8"  # congested centre (a little darker)
TEXT_OUTLINE = [patheffects.withStroke(linewidth=2.2, foreground="white")]


def draw_city(model, fig=None):
    """Draw the city grid from the model with matplotlib.

    A custom drawing (instead of Mesa's make_space_component) because the
    taxis' planned routes and stops come from the model, not from single
    agents. Layers: congestion zones (when on), district grid, planned
    routes, planned stops, waiting
    passengers (one marker per district with a count), abandoned passengers
    (at their origin), taxis with an "on board / capacity" label.
    """
    # Wide aspect (~0.56) so the whole grid fits one panel of Mesa's dashboard.
    fig = fig or Figure(figsize=(8.6, 4.8), layout="constrained")
    ax = fig.add_subplot()
    w, h = model.width, model.height
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, w, 5))
    ax.set_yticks(range(0, h, 5))
    ax.set_xticks(np.arange(-0.5, w, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, h, 1), minor=True)
    ax.grid(which="minor", color="#e8e8e8", linewidth=0.6)
    ax.tick_params(which="both", length=0, labelsize=7, colors="#777777")
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    status = "running" if model.running else "finished"
    ax.set_title(f"Minute {model.minute} / {model.duration} ({status})", fontsize=11)

    # Congestion zones: the ring square first, the centre square on top.
    if model.congestion != "off":
        x0, y0 = congestion_center(w, h)
        for pad, color in ((1, RING_SHADE), (0, CENTER_SHADE)):
            size = CONGESTION_CENTER_SIZE + 2 * pad
            ax.add_patch(Rectangle((x0 - pad - 0.5, y0 - pad - 0.5), size, size,
                                   facecolor=color, edgecolor="none", zorder=0))

    # Planned routes and stops, in the colour of the taxi's state.
    pickups, dropoffs = [], []
    for taxi in model.taxis:
        if not taxi.stops:
            continue
        color = TAXI_COLORS[taxi.state]
        xs, ys = zip(*taxi.route_cells())
        ax.plot(xs, ys, color=color, linewidth=1.4, alpha=0.55, zorder=2,
                solid_capstyle="round", solid_joinstyle="round")
        for stop in taxi.stops:
            x, y = stop_district(stop)
            (pickups if stop[0] == PICKUP else dropoffs).append((x, y, color))
    for points, marker in ((pickups, "^"), (dropoffs, "v")):
        if points:
            x, y, c = zip(*points)
            ax.scatter(x, y, marker=marker, s=34, c=c, edgecolors="#333333",
                       linewidths=0.5, zorder=3)

    # Passengers outside taxis, grouped per district (count when > 1).
    groups = Counter()
    gave_up = Counter()
    for p in model.passengers:
        if p.status == ABANDONED:
            gave_up[p.origin] += 1  # left the grid; marked where they waited
            continue
        if p.pos is None:
            continue  # completed: left the map
        if p.status in (WAITING, ASSIGNED):
            groups[(p.pos, p.status)] += 1
        elif p.status == NOT_COMPLETED:
            groups[(p.pos, NOT_COMPLETED)] += 1
    dots = {"x": [], "y": [], "s": [], "c": []}  # one scatter call for all dots
    crosses = []
    for ((x, y), status), count in groups.items():
        if status == NOT_COMPLETED:
            crosses.append((x + 0.28, y + 0.28))
            if count > 1:
                ax.text(x + 0.28, y - 0.05, str(count), fontsize=6, ha="center",
                        va="top", zorder=6, path_effects=TEXT_OUTLINE)
            continue
        dx = -0.27 if status == WAITING else 0.27
        dots["x"].append(x + dx)
        dots["y"].append(y + 0.27)
        dots["s"].append(34 if count == 1 else 95)
        dots["c"].append(WAITING_COLOR if status == WAITING else ASSIGNED_COLOR)
        if count > 1:
            ax.text(x + dx, y + 0.27, str(count), fontsize=6.5, ha="center",
                    va="center", fontweight="bold", zorder=6)
    if dots["x"]:
        ax.scatter(dots["x"], dots["y"], s=dots["s"], c=dots["c"],
                   edgecolors="#333333", linewidths=0.5, zorder=4)
    if crosses:
        ax.scatter(*zip(*crosses), marker="x", s=30, c="black", zorder=4)
    if gave_up:
        rings = [(x - 0.28, y - 0.28) for x, y in gave_up]
        ax.scatter(*zip(*rings), marker="o", s=30, facecolors="none",
                   edgecolors=ABANDONED_COLOR, linewidths=1.3, zorder=4)
        for (x, y), count in gave_up.items():
            if count > 1:
                ax.text(x - 0.28, y - 0.62, str(count), fontsize=6, ha="center",
                        va="center", zorder=6, path_effects=TEXT_OUTLINE)

    # Taxis: square in the state colour, label "on board / capacity".
    if model.taxis:
        x, y = zip(*(t.pos for t in model.taxis))
        colors = [TAXI_COLORS[t.state] for t in model.taxis]
        ax.scatter(x, y, marker="s", s=120, c=colors, edgecolors="black",
                   linewidths=0.8, zorder=5)
        for taxi in model.taxis:
            tx, ty = taxi.pos
            ax.text(tx + 0.12, ty - 0.33, f"{len(taxi.onboard)}/{taxi.capacity}",
                    fontsize=6.5, ha="left", va="top", zorder=6,
                    path_effects=TEXT_OUTLINE)

    handles = [
        Line2D([], [], marker="s", ls="", color=c, markeredgecolor="black",
               markersize=8, label=f"taxi: {s.replace('_', ' ')}")
        for s, c in TAXI_COLORS.items()
    ] + [
        Line2D([], [], color="#777777", linewidth=1.4, alpha=0.7,
               label="planned route (taxi colour)"),
        Line2D([], [], marker="^", ls="", color="#bbbbbb", markeredgecolor="#333333",
               label="planned pickup"),
        Line2D([], [], marker="v", ls="", color="#bbbbbb", markeredgecolor="#333333",
               label="planned drop-off"),
        Line2D([], [], marker="o", ls="", color=WAITING_COLOR,
               markeredgecolor="#333333", label="waiting, no taxi yet"),
        Line2D([], [], marker="o", ls="", color=ASSIGNED_COLOR,
               markeredgecolor="#333333", label="waiting, taxi assigned"),
        Line2D([], [], marker="x", ls="", color="black",
               label="not completed (deadline)"),
        Line2D([], [], marker="o", ls="", markerfacecolor="none",
               markeredgecolor=ABANDONED_COLOR, markeredgewidth=1.3,
               label="abandoned (gave up waiting)"),
    ]
    if model.congestion != "off":
        handles += [
            Patch(facecolor=CENTER_SHADE, label=f"congestion x{CENTER_FACTOR} (centre)"),
            Patch(facecolor=RING_SHADE, label=f"congestion x{RING_FACTOR} (ring)"),
        ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1),
              fontsize=8, frameon=False, alignment="left",
              title="2/4 = on board / seats\nnumber in dot = passengers there",
              title_fontsize=7)
    return fig


def GridView(model):
    # Redraw only when the model or its minute changed.
    return solara.FigureMatplotlib(draw_city(model), format="png",
                                   dependencies=[id(model), model.minute])


def fmt(value, digits=1):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def StatusPanel(model):
    """Simulation time, configuration and the main results."""
    m = model.latest_metrics
    status = "running" if model.running else "finished (deadline reached)"
    patience = ("off" if model.patience_max is None
                else f"{model.patience_min}-{model.patience_max} min")
    text = f"""
### Minute {model.minute} / {model.duration} — {status}

**Configuration:** {len(model.taxis)} taxis · capacity {model.capacity} ·
sharing `{model.sharing_mode}` · arrivals `{model.arrival_mode}`
(window {model.arrival_window} min) · boarding {model.boarding_minutes} min/stop ·
patience {patience} · congestion `{model.congestion}` ·
max extra delay {model.max_extra_delay} min · {model.width}×{model.height} districts ·
seed {model.seed}

| Metric | Value |
|---|---|
| Passengers created | {m['created']} |
| Waiting / assigned / travelling | {m['waiting']} / {m['assigned']} / {m['travelling']} |
| Completed | {m['completed']} ({fmt(m['completed_pct'])} %) |
| Not completed at deadline | {m['not_completed']} |
| Abandoned (patience exceeded) | {m['abandoned']} ({fmt(m['abandoned_pct'])} %) |
| Acceptable trips (of created) | {fmt(m['acceptable_pct'])} % |
| Avg waiting time (completed, n={m['completed']}) | {fmt(m['avg_wait_completed'])} min |
| Avg total journey time (completed, n={m['completed']}) | {fmt(m['avg_total_completed'])} min |
| Avg extra delay (completed, n={m['completed']}) | {fmt(m['avg_extra_delay_completed'])} min |
| Avg extra delay (shared rides, n={m['shared_completed']}) | {fmt(m['avg_extra_delay_shared'])} min |
| Avg waiting incl. unserved (all, n={m['created']}) | {fmt(m['avg_wait_censored'])} min |
| Taxi distance: total / empty / occupied | {m['total_distance']} / {m['empty_distance']} / {m['occupied_distance']} districts |
| Empty distance share | {fmt(m['empty_distance_pct'])} % |
| Passenger distance (passenger-districts) | {m['passenger_distance']} |
| Avg occupancy (passenger ÷ taxi distance) | {fmt(m['avg_occupancy'], 2)} |
| Distance per completed passenger | {fmt(m['distance_per_completed'])} districts |
| Taxi utilization (passenger on board) | {fmt(m['utilization_pct'])} % |
| Messages exchanged | {m['messages']} |
"""
    return solara.Markdown(text)


model_params = {
    "num_taxis": {"type": "SliderInt", "value": DEFAULTS["num_taxis"],
                  "label": "Number of taxis", "min": 1, "max": 20, "step": 1},
    "num_passengers": {"type": "SliderInt", "value": DEFAULTS["num_passengers"],
                       "label": "Number of passengers", "min": 1, "max": 200,
                       "step": 1},
    "capacity": {"type": "Select", "value": 2, "values": list(CAPACITIES),
                 "label": "Taxi capacity"},
    "sharing_mode": {"type": "Select", "value": "detour",
                     "values": list(SHARING_MODES), "label": "Sharing mode"},
    "boarding_minutes": {"type": "SliderInt", "value": BOARDING_MINUTES,
                         "label": "Boarding time per stop (min)", "min": 0,
                         "max": 3, "step": 1},
    "patience_min": {"type": "SliderInt", "value": PATIENCE_MIN,
                     "label": "Patience min (min)", "min": 1, "max": 60,
                     "step": 1},
    "patience_max": {"type": "SliderInt", "value": 0,
                     "label": "Patience max (min, 0 = never abandon)", "min": 0,
                     "max": 60, "step": 1},
    "congestion": {"type": "Select", "value": DEFAULTS["congestion"],
                   "values": list(CONGESTION_MODES), "label": "Traffic congestion"},
    "arrival_mode": {"type": "Select", "value": DEFAULTS["arrival_mode"],
                     "values": list(ARRIVAL_MODES), "label": "Passenger arrivals"},
    "arrival_window": {"type": "SliderInt", "value": DEFAULTS["arrival_window"],
                       "label": "Gradual arrival window (min)", "min": 1,
                       "max": 240, "step": 1},
    "duration": {"type": "SliderInt", "value": DEFAULTS["duration"],
                 "label": "Duration (min)", "min": 10, "max": 240, "step": 10},
    "seed": {"type": "SliderInt", "value": DEFAULTS["seed"], "label": "Seed",
             "min": 1, "max": 100, "step": 1},
}

# Time-series charts: one panel per measure group (series -> colour).
CHART_PANELS = [
    ("Passengers by status", {"waiting": "#e53935", "assigned": "#fdd835",
                              "travelling": "#1e88e5", "completed": "#43a047",
                              "not_completed": "#000000",
                              "abandoned": ABANDONED_COLOR}),
    ("Average times, completed (min)", {"avg_wait_completed": "#ff9800",
                                        "avg_total_completed": "#1e88e5",
                                        "avg_extra_delay_completed": "#8e24aa"}),
    ("Taxi distance (districts)", {"total_distance": "#333333",
                                   "occupied_distance": "#1e88e5",
                                   "empty_distance": "#9e9e9e"}),
    ("Taxi utilization (%)", {"utilization_pct": "#43a047"}),
]


def ChartsPanel(model):
    """All charts in one figure: one PNG per step instead of one per chart,
    which keeps Play responsive (each matplotlib image costs ~0.1-0.3 s)."""
    df = model.datacollector.get_model_vars_dataframe()
    # 2x2 small multiples sized for one half-width panel of Mesa's dashboard.
    fig = Figure(figsize=(8, 4.6), layout="constrained")
    for ax, (title, series) in zip(fig.subplots(2, 2).flat, CHART_PANELS):
        for column, color in series.items():
            label = column.replace("_completed", "") if column.startswith("avg_") else column
            ax.plot(df["minute"], df[column], color=color, linewidth=1.6,
                    label=label.replace("_", " "))
        ax.set_title(title, fontsize=9)
        ax.set_xlim(0, model.duration)
        ax.tick_params(labelsize=7)
        ax.grid(color="#e6e5e0", linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        if len(series) > 1:
            ax.legend(fontsize=6, frameon=False, loc="upper left")
    fig.supxlabel("minute", fontsize=8)
    # Redraw only when the model or its minute changed.
    return solara.FigureMatplotlib(fig, format="png",
                                   dependencies=[id(model), model.minute])


@solara.component
def Page():
    # One model per browser session; SolaraViz's Reset replaces it with a new
    # model built from the sidebar parameters.
    model = solara.use_memo(lambda: TaxiModel(capacity=2, sharing_mode="detour"), [])
    # Mesa's dashboard needs the Vue 2 widget stack (ipyvue/ipyvuetify 1.x,
    # pinned in requirements.txt); with the 3.x packages the main area is blank.
    SolaraViz(
        model,
        components=[GridView, StatusPanel, ChartsPanel],
        model_params=model_params,
        name=f"Taxi sharing (max extra delay {MAX_EXTRA_DELAY_MINUTES} min)",
    )
