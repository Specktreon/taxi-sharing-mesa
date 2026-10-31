"""The interface code: map, legend sections, status panel (no browser)."""

import itertools

import pytest
from matplotlib.figure import Figure

import app

FEATURES = ["buses", "walking", "congestion", "patience"]


@pytest.mark.parametrize("flags", list(itertools.product([False, True], repeat=4)),
                         ids=lambda f: "".join("BWCP"[i] if on else "-"
                                               for i, on in enumerate(f)))
def test_map_and_panels_for_every_feature_combination(flags):
    on = dict(zip(FEATURES, flags))
    m = app.UITaxiModel(num_passengers=60, seed=2, **on)
    for _ in range(30):
        m.step()
    fig = app.draw_city(m)
    ax = fig.axes[0]
    legend_texts = [t.get_text() for t in ax.get_legend().get_texts()]
    expected = ["Taxis"] + (["Buses"] if on["buses"] else []) + ["Passengers"] + (
        ["Zones"] if on["congestion"] else [])
    assert [t for t in legend_texts if t in ("Taxis", "Buses", "Passengers", "Zones")] \
        == expected
    box = " ".join(t.get_text() for t in ax.texts)
    for name in FEATURES:
        assert f"{name.capitalize()} {'on' if on[name] else 'off'}" in box
    assert ("abandoned (at origin)" in legend_texts) == on["patience"]
    assert ("taxi: walking to pickup" in legend_texts) == on["walking"]

    status = app.StatusPanel(m).args[0]  # the Markdown text
    table = status[status.index("| Metric |"):].strip().splitlines()
    assert all(row.startswith("|") for row in table)  # one unbroken table
    assert ("Bus passengers" in status) == on["buses"]


def test_buses_and_bus_passengers_are_drawn():
    m = app.UITaxiModel(buses=True, num_passengers=90, seed=1)
    while m.minute < 40:
        m.step()
    fig = app.draw_city(m, Figure())
    labels = [t.get_text() for t in fig.axes[0].texts]
    assert sum(label.endswith("/10") for label in labels) == len(m.buses) == 12
