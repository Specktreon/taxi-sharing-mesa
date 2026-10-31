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
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from mesa.visualization import SolaraViz

from agents import (ABANDONED, ASSIGNED, AT_STOP, BUS, NOT_COMPLETED, PICKUP,
                    RIDING, TRAVELLING, WAITING, stop_district)
from config import (CAPACITIES, CENTER_FACTOR, DEFAULTS, MAX_EXTRA_DELAY_MINUTES,
                    RING_FACTOR, SHARING_MODES, feature_params)
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
WALK_COLOR = "#00897b"  # teal diamond + arrow: walking to the pickup district
RING_SHADE = "#fff1dc"  # congestion ring (light)
CENTER_SHADE = "#fde0b8"  # congested centre (a little darker)
# One colour per bus line, distinct from the taxi and passenger colours.
BUS_LINE_COLORS = {"H1": "#d81b60", "H2": "#283593", "H3": "#00838f",
                   "V1": "#9e9d24", "V2": "#5e35b1", "V3": "#37474f"}
TEXT_OUTLINE = [patheffects.withStroke(linewidth=2.2, foreground="white")]


class UITaxiModel(TaxiModel):
    """TaxiModel for the sidebar: only the varied parameters, plus the four
    feature checkboxes, mapped to model parameters by config.feature_params.
    Every other setting keeps its fixed default from config.py. (Mesa's Reset
    builds a new model from this exact signature, so it lists every sidebar
    name and has no **kwargs.)"""

    def __init__(self, sharing_mode="detour", capacity=2,
                 num_taxis=DEFAULTS["num_taxis"],
                 num_passengers=DEFAULTS["num_passengers"], seed=DEFAULTS["seed"],
                 buses=False, walking=False, congestion=False, patience=False):
        self.features = {"buses": buses, "walking": walking,
                         "congestion": congestion, "patience": patience}
        super().__init__(sharing_mode=sharing_mode, capacity=capacity,
                         num_taxis=num_taxis, num_passengers=num_passengers,
                         seed=seed, **feature_params(**self.features))


def active_features(model):
    """Which of the four features a model runs with."""
    return {"Buses": model.buses_on, "Walking": bool(model.walk_radius),
            "Congestion": model.congestion != "off",
            "Patience": model.patience_max is not None}


def draw_zones(ax, model):
    """Congestion zones: the ring rectangle first, the centre on top."""
    x0, y0, size_x, size_y = congestion_center(model.width, model.height)
    for pad, color in ((1, RING_SHADE), (0, CENTER_SHADE)):
        ax.add_patch(Rectangle((x0 - pad - 0.5, y0 - pad - 0.5),
                               size_x + 2 * pad, size_y + 2 * pad,
                               facecolor=color, edgecolor="none", zorder=0))


def draw_bus_network(ax, model):
    """Bus lines as wide light roads, stops as small square signs on them,
    buses as rounded boxes along their line with "on board/capacity"."""
    for line in model.bus_lines:
        color = BUS_LINE_COLORS[line.name]
        xs, ys = zip(*line.cells)
        ax.plot(xs, ys, color=color, alpha=0.22, linewidth=7.5,
                solid_capstyle="butt", zorder=1)
        sx, sy = zip(*line.stop_index)
        ax.scatter(sx, sy, marker="s", s=13, facecolors="white",
                   edgecolors=color, linewidths=1.0, zorder=2)
    for bus in model.buses:
        color = BUS_LINE_COLORS[bus.line.name]
        x, y = bus.pos
        horizontal = bus.line.name.startswith("H")
        bw, bh = (1.5, 0.72) if horizontal else (0.72, 1.5)
        # Below the taxis (zorder 5), so a taxi in the same district stays visible.
        ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh,
                                    boxstyle="round,pad=0,rounding_size=0.28",
                                    facecolor=color, edgecolor="#222222",
                                    linewidth=0.7, zorder=4.5))
        # Horizontal label on a small white tag, readable on every line.
        ax.text(x, y, f"{len(bus.onboard)}/{bus.capacity}", fontsize=6,
                color="#111111", fontweight="bold", ha="center", va="center",
                zorder=4.6,
                bbox={"boxstyle": "round,pad=0.12", "facecolor": "white",
                      "edgecolor": color, "linewidth": 0.6, "alpha": 0.92})


def legend_handles(model):
    """Legend entries grouped in sections; only active sections are shown.
    Returns (handles, section titles)."""
    feats = active_features(model)
    sections = {"Taxis": [
        Line2D([], [], marker="s", ls="", color=c, markeredgecolor="black",
               markersize=7, label=f"{s.replace('_', ' ')}")
        for s, c in TAXI_COLORS.items()
    ] + [
        Line2D([], [], color="#777777", linewidth=1.4, alpha=0.7,
               label="planned route (taxi colour)"),
        Line2D([], [], marker="^", ls="", color="#bbbbbb", markeredgecolor="#333333",
               label="planned pickup"),
        Line2D([], [], marker="v", ls="", color="#bbbbbb", markeredgecolor="#333333",
               label="planned drop-off"),
    ]}
    if feats["Buses"]:
        sections["Buses"] = [
            Line2D([], [], color=c, alpha=0.35, linewidth=6, label=f"line {name}")
            for name, c in BUS_LINE_COLORS.items()
        ] + [
            Line2D([], [], marker="s", ls="", markerfacecolor="white",
                   markeredgecolor="#555555", markersize=5, label="bus stop"),
            Patch(facecolor="#777777", edgecolor="#222222",
                  label="bus (on board / 10)"),
        ]
    passengers = [
        Line2D([], [], marker="o", ls="", color=WAITING_COLOR,
               markeredgecolor="#333333", label="taxi: waiting, no taxi yet"),
        Line2D([], [], marker="o", ls="", color=ASSIGNED_COLOR,
               markeredgecolor="#333333", label="taxi: taxi assigned"),
    ]
    if feats["Walking"]:
        passengers.append(Line2D([], [], marker="D", ls="--", color=WALK_COLOR,
                                 markeredgecolor="#333333", markersize=5,
                                 label="taxi: walking to pickup"))
    if feats["Buses"]:
        passengers += [
            Line2D([], [], marker="p", ls="", color="#777777",
                   markeredgecolor="#222222", markersize=7,
                   label="bus: waiting at stop (line colour)"),
            Line2D([], [], marker="p", ls="", markerfacecolor="white",
                   markeredgecolor="#555555", markersize=7, label="bus: walking"),
        ]
    if feats["Patience"]:
        passengers.append(Line2D([], [], marker="o", ls="", markerfacecolor="none",
                                 markeredgecolor=ABANDONED_COLOR, markeredgewidth=1.3,
                                 label="abandoned (at origin)"))
    passengers.append(Line2D([], [], marker="x", ls="", color="black",
                             label="not completed (deadline)"))
    sections["Passengers"] = passengers
    if feats["Congestion"]:
        sections["Zones"] = [
            Patch(facecolor=CENTER_SHADE, label=f"congestion x{CENTER_FACTOR} (centre)"),
            Patch(facecolor=RING_SHADE, label=f"congestion x{RING_FACTOR} (ring)"),
        ]
    handles, titles = [], []
    for title, entries in sections.items():
        header = Line2D([], [], ls="", marker="", label=title)
        handles += [header] + entries
        titles.append(title)
    return handles, titles


def draw_city(model, fig=None):
    """Draw the city grid from the model with matplotlib.

    A custom drawing (instead of Mesa's make_space_component) because the
    taxis' planned routes and stops, and the bus lines, come from the model,
    not from single agents. Layers: congestion zones, district grid, bus
    roads and stops, planned taxi routes and stops, passengers outside
    vehicles, buses, taxis. A box above the map lists the active features;
    the legend shows only the sections that are active.
    """
    # Square map plus a legend column; sized for one dashboard panel.
    fig = fig or Figure(figsize=(9.6, 7.0), layout="constrained")
    ax = fig.add_subplot()
    w, h = model.width, model.height
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, w, 5))
    ax.set_yticks(range(0, h, 5))
    ax.set_xticks(np.arange(-0.5, w, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, h, 1), minor=True)
    ax.grid(which="minor", color="#ececec", linewidth=0.5)
    ax.tick_params(which="both", length=0, labelsize=7, colors="#777777")
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    status = "running" if model.running else "finished"
    ax.set_title(f"Minute {model.minute} / {model.duration} ({status})",
                 fontsize=11, pad=22)
    features = " · ".join(f"{name} {'on' if on else 'off'}"
                          for name, on in active_features(model).items())
    ax.text(0.5, 1.012, features, transform=ax.transAxes, ha="center",
            va="bottom", fontsize=8, color="#333333",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "#f5f5f2",
                  "edgecolor": "#cccccc", "linewidth": 0.6})

    if model.congestion != "off":
        draw_zones(ax, model)
    if model.buses_on:
        draw_bus_network(ax, model)

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
    walkers = []
    bus_waiting = Counter()  # (stop, line name) -> passengers queued there
    bus_walkers = []
    for p in model.passengers:
        if p.status == ABANDONED:
            gave_up[p.origin] += 1  # left the grid; marked where they waited
            continue
        if p.mode == BUS and p.status in (WAITING, TRAVELLING):
            if p.bus_stage == AT_STOP:
                bus_waiting[(p.pos, p.bus_line.name)] += 1
            elif p.bus_stage != RIDING:
                bus_walkers.append((p.pos, p.bus_line.name))
            continue  # riders are drawn inside their bus (its count)
        if p.walking:
            walkers.append((p.pos, p.pickup_district))
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
    for (x, y), target in walkers:
        ax.annotate("", xy=target, xytext=(x, y), zorder=4,
                    arrowprops={"arrowstyle": "->", "color": WALK_COLOR,
                                "linewidth": 1.1, "linestyle": "--"})
    if walkers:
        diamonds = [(x - 0.27, y - 0.27) for (x, y), _ in walkers]
        ax.scatter(*zip(*diamonds), marker="D", s=26, c=WALK_COLOR,
                   edgecolors="#333333", linewidths=0.5, zorder=4)
    if gave_up:
        rings =[(x - 0.28, y - 0.28) for x, y in gave_up]
        ax.scatter(*zip(*rings), marker="o", s=30, facecolors="none",
                   edgecolors=ABANDONED_COLOR, linewidths=1.3, zorder=4)
        for (x, y), count in gave_up.items():
            if count > 1:
                ax.text(x - 0.28, y - 0.62, str(count), fontsize=6, ha="center",
                        va="center", zorder=6, path_effects=TEXT_OUTLINE)
    # Bus passengers: pentagons in their line colour, beside the road.
    for ((x, y), name), count in bus_waiting.items():
        ax.scatter(x + 0.32, y - 0.32, marker="p", s=42 if count == 1 else 80,
                   c=BUS_LINE_COLORS[name], edgecolors="#222222", linewidths=0.6,
                   zorder=4)
        if count > 1:
            ax.text(x + 0.32, y - 0.32, str(count), fontsize=5.5, color="white",
                    fontweight="bold", ha="center", va="center", zorder=6)
    for (x, y), name in bus_walkers:
        ax.scatter(x + 0.32, y - 0.32, marker="p", s=38, facecolors="white",
                   edgecolors=BUS_LINE_COLORS[name], linewidths=1.2, zorder=4)

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

    handles, titles = legend_handles(model)
    legend = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1),
                       fontsize=7.5, frameon=False, alignment="left",
                       handlelength=1.8, labelspacing=0.45,
                       title="2/4 = on board / seats\nnumber = passengers there",
                       title_fontsize=7)
    for text in legend.get_texts():
        if text.get_text() in titles:  # section headers
            text.set_fontweight("bold")
            text.set_fontsize(8.5)
            text.set_x(-22)  # pull the header left over its empty handle
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
    walking = (f"to neighbour district ({model.walk_minutes_per_district} min/district)"
               if model.walk_radius else "off")
    by_mode = ""  # extra table rows (each starting with a newline) with buses on
    if model.buses_on:
        by_mode = "\n" + "\n".join(
            f"| {label}: completed / avg wait / avg total time | "
            f"{fmt(m[f'completed_pct_{mode}'])} % / "
            f"{fmt(m[f'avg_wait_completed_{mode}'])} min / "
            f"{fmt(m[f'avg_total_completed_{mode}'])} min |"
            for mode, label in (("taxi", "Taxi passengers"), ("bus", "Bus passengers"))
        ) + (f"\n| Bus share / bus distance / avg bus occupancy | "
             f"{fmt(m['bus_share_pct'])} % / {m['bus_distance']} districts / "
             f"{fmt(m['avg_bus_occupancy'], 2)} |")
    text = f"""
### Minute {model.minute} / {model.duration} — {status}

**Configuration:** {len(model.taxis)} taxis · capacity {model.capacity} ·
sharing `{model.sharing_mode}` · arrivals `{model.arrival_mode}`
(window {model.arrival_window} min) · boarding {model.boarding_minutes} min/stop ·
patience {patience} · congestion `{model.congestion}` ·
walking {walking} · buses {"on" if model.buses_on else "off"} ·
max extra delay {model.max_extra_delay} min · {model.width}×{model.height} districts ·
seed {model.seed}

| Metric | Value |
|---|---|
| Passengers created | {m['created']} |
| Waiting / assigned / travelling | {m['waiting']} / {m['assigned']} / {m['travelling']} |
| Completed | {m['completed']} ({fmt(m['completed_pct'])} %) |{by_mode}
| Not completed at deadline | {m['not_completed']} |
| Abandoned (patience exceeded) | {m['abandoned']} ({fmt(m['abandoned_pct'])} %) |
| Acceptable trips (of created) | {fmt(m['acceptable_pct'])} % |
| Avg waiting time (completed, n={m['completed']}) | {fmt(m['avg_wait_completed'])} min |
| Avg total journey time (completed, n={m['completed']}) | {fmt(m['avg_total_completed'])} min |
| Avg extra delay (completed, n={m['completed']}) | {fmt(m['avg_extra_delay_completed'])} min |
| Avg extra delay (shared rides, n={m['shared_completed']}) | {fmt(m['avg_extra_delay_shared'])} min |
| Avg waiting incl. unserved (all, n={m['created']}) | {fmt(m['avg_wait_censored'])} min |
| Walked to a neighbour district (completed) | {fmt(m['walked_pct'])} % · avg walk {fmt(m['avg_walk_minutes'])} min |
| Taxi distance: total / empty / occupied | {m['total_distance']} / {m['empty_distance']} / {m['occupied_distance']} districts |
| Empty distance share | {fmt(m['empty_distance_pct'])} % |
| Passenger distance (passenger-districts) | {m['passenger_distance']} |
| Avg occupancy (passenger ÷ taxi distance) | {fmt(m['avg_occupancy'], 2)} |
| Distance per completed passenger | {fmt(m['distance_per_completed'])} districts |
| Taxi utilization (passenger on board) | {fmt(m['utilization_pct'])} % |
| Messages exchanged | {m['messages']} |
"""
    return solara.Markdown(text)


# Sidebar: only what varies between scenarios. Everything else is fixed in
# config.py (30x30 map, 120 min, gradual arrivals over 90 min, ...).
model_params = {
    "sharing_mode": {"type": "Select", "value": "detour",
                     "values": list(SHARING_MODES), "label": "Sharing mode"},
    "capacity": {"type": "Select", "value": 2, "values": list(CAPACITIES),
                 "label": "Taxi capacity"},
    "num_taxis": {"type": "SliderInt", "value": DEFAULTS["num_taxis"],
                  "label": "Number of taxis", "min": 1, "max": 40, "step": 1},
    "num_passengers": {"type": "SliderInt", "value": DEFAULTS["num_passengers"],
                       "label": "Number of passengers", "min": 1, "max": 200,
                       "step": 1},
    "seed": {"type": "SliderInt", "value": DEFAULTS["seed"], "label": "Seed",
             "min": 1, "max": 100, "step": 1},
    "buses": {"type": "Checkbox", "value": False, "label": "Buses"},
    "walking": {"type": "Checkbox", "value": False,
                "label": "Walking to neighbour district"},
    "congestion": {"type": "Checkbox", "value": False, "label": "Traffic congestion"},
    "patience": {"type": "Checkbox", "value": False, "label": "Passenger patience"},
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
    model = solara.use_memo(UITaxiModel, [])
    # Mesa's dashboard needs the Vue 2 widget stack (ipyvue/ipyvuetify 1.x,
    # pinned in requirements.txt); with the 3.x packages the main area is blank.
    SolaraViz(
        model,
        components=[GridView, StatusPanel, ChartsPanel],
        model_params=model_params,
        name=f"Taxi sharing (max extra delay {MAX_EXTRA_DELAY_MINUTES} min)",
        # Model steps in the UI thread, so each matplotlib frame shows a
        # finished minute. Mesa 3.5.1 always shows its "Use Threads" checkbox
        # (no option to hide it); with it ticked the map can be drawn while
        # the model is mid-step. Raise "Render Interval" to go faster instead.
        use_threads=False,
    )
