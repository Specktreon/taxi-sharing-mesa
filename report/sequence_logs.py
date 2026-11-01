"""Message logs of small hand-made scenarios, for the sequence diagrams.

Run from the project folder: python report/sequence_logs.py
Each scenario builds a deterministic TaxiModel (fixed taxi_starts / requests,
like tests/helpers.make_model), records every Message by wrapping
TaxiModel.send on the instance (the model code is not changed), and records
the non-message events (boarding, walking, abandoning, bus stages) by
comparing the passengers' state before and after every step. The logs are
printed and saved to report/logs/<name>.json; report/make_figures.py draws them.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")  # project modules (run from the project folder)
from agents import ABANDONED, BUS, COMPLETED  # noqa: E402
from model import TaxiModel  # noqa: E402

LOGS = Path("report/logs")


def make_model(taxi_starts, requests, **kwargs):
    """Hand-made scenario on a 20x20 grid (as tests/helpers.make_model), with
    1-minute boarding as in the study."""
    params = {"duration": 60, "capacity": 1, "sharing_mode": "none",
              "boarding_minutes": 1, "width": 20, "height": 20}
    params.update(kwargs)
    return TaxiModel(taxi_starts=taxi_starts, requests=requests, **params)


def record(model, names, until):
    """Step the model, recording messages and events until `until(model)`."""
    messages, events = [], []
    original = model.send

    def send(message):
        messages.append({"minute": message.time, "sender": message.sender,
                         "receiver": message.receiver, "type": message.type,
                         "data": {k: (list(v) if isinstance(v, tuple) else v)
                                  for k, v in message.data.items()}})
        original(message)

    model.send = send  # instance attribute: only this model is wrapped

    def state(p):
        return {"status": p.status, "pos": p.pos, "pickup": p.pickup_time,
                "stage": p.bus_stage, "alight": p.alight_time}

    def event(minute, p, text):
        events.append({"minute": minute, "agent": p.unique_id, "text": text})

    while model.running and not until(model):
        before = {p.unique_id: state(p) for p in model.passengers}
        model.step()
        for p in model.passengers:
            old, new = before.get(p.unique_id), state(p)
            if old is None:
                continue
            # A walk: the passenger moved on its own. A taxi passenger walks
            # from its origin to another pickup district (possibly in the same
            # step as its CONFIRM); a bus passenger to or from a stop.
            taxi_walk = (p.mode != BUS and old["pos"] == p.origin
                         and new["pos"] == p.pickup_district != p.origin)
            on_foot = taxi_walk or old["stage"] in ("to_stop", "to_destination")
            if on_foot and new["pos"] not in (None, old["pos"]):
                event(model.minute, p, f"walks to {tuple(new['pos'])}")
            if new["stage"] == "at_stop" and old["stage"] == "to_stop":
                event(model.minute, p, "reaches the stop, waits")
            if new["pickup"] is not None and old["pickup"] is None:
                vehicle = "bus" if p.mode == BUS else names[p.taxi.unique_id]
                where = tuple(p.pickup_district if p.mode != BUS else p.board_stop)
                event(new["pickup"], p, f"boards {vehicle} at {where}")
            if new["alight"] is not None and old["alight"] is None:
                event(new["alight"], p, f"leaves the bus at {tuple(p.alight_stop)}")
            if new["status"] == ABANDONED and old["status"] != ABANDONED:
                event(p.abandon_time, p, "abandons (patience over)")
            if new["status"] == COMPLETED and old["status"] != COMPLETED:
                delay = ("" if p.extra_delay is None
                         else f", extra delay {p.extra_delay} min")
                event(p.arrival_time, p, f"arrives at {tuple(p.destination)}{delay}")
    return messages, sorted(events, key=lambda e: e["minute"])


def scenario(name, title, model, names, until, note=""):
    """Run a scenario; `names` maps unique_id -> lane label (lane order)."""
    passengers = {p.unique_id: p for p in model.passengers}
    messages, events = record(model, names, until)
    passengers.update({p.unique_id: p for p in model.passengers})
    return {"name": name, "title": title, "note": note,
            "lanes": [{"id": uid, "label": label} for uid, label in names.items()],
            "origins": {str(uid): list(p.origin) for uid, p in passengers.items()},
            "patience": {str(uid): p.patience for uid, p in passengers.items()},
            "messages": messages, "events": events}


def rejection():
    # One free taxi, two passengers requesting in the same minute. Both get a
    # PROPOSE and ACCEPT the same taxi; the lower id is confirmed, the other
    # rejected, and it asks again every minute until a taxi is free.
    m = make_model([(0, 0)], [(0, (2, 0), (2, 5)), (0, (3, 0), (3, 5))])
    taxi = m.taxis[0].unique_id
    p1, p2 = (m.passengers[0].unique_id, m.passengers[1].unique_id)
    return scenario("rejection", "a) Rejection and retry (single rides)", m,
                    {p1: "Passenger P1", taxi: "Taxi A", p2: "Passenger P2"},
                    until=lambda mod: mod.passengers[1].pickup_time is not None)


def sharing():
    # The taxi carries P1 along y = 0; at minute 2 P2 asks for a short trip
    # one row up. Detour sharing inserts P2's pickup and drop-off.
    m = make_model([(0, 0)], [(0, (0, 0), (10, 0)), (2, (5, 1), (8, 1))],
                   capacity=2, sharing_mode="detour")
    taxi = m.taxis[0].unique_id
    p1 = m.passengers[0].unique_id
    p2 = p1 + 1  # created at minute 2

    def done(mod):
        return all(p.status == COMPLETED for p in mod.passengers) and len(
            mod.passengers) == 2

    return scenario("sharing", "b) Sharing with a detour (capacity 2)", m,
                    {p1: "Passenger P1", taxi: "Taxi A", p2: "Passenger P2"},
                    until=done)


def walking():
    # The taxi at (5, 0) reaches the neighbour (5, 1) in 1 minute; the passenger
    # walks 1 minute per district, so it can be there first.
    m = make_model([(5, 0)], [(0, (5, 2), (5, 8))], walk_radius=1,
                   walk_minutes_per_district=1)
    taxi, p = m.taxis[0].unique_id, m.passengers[0].unique_id
    return scenario("walking", "c) Walking to a neighbouring district", m,
                    {p: "Passenger P", taxi: "Taxi A"},
                    until=lambda mod: mod.passengers[0].pickup_time is not None)


def patience():
    # The only taxi is 10 minutes away; the passenger's patience is 5 minutes,
    # so it never accepts and abandons at minute 5.
    m = make_model([(0, 0)], [(0, (10, 0), (10, 3))], patience_min=5,
                   patience_max=5)
    taxi, p = m.taxis[0].unique_id, m.passengers[0].unique_id
    return scenario("patience", "d) Patience: offer too late, abandon", m,
                    {p: "Passenger P", taxi: "Taxi A"},
                    until=lambda mod: mod.passengers[0].status == ABANDONED)


def bus():
    # A bus rider (both ends near line H1 on 20x20): no message at all.
    m = make_model([(10, 10)], [(0, (0, 6), (19, 4))], buses=True)
    p = m.passengers[0]
    bus_agent = next(b for b in m.buses if b.line is p.bus_line and b.index == 19)
    return scenario("bus", "e) Bus passenger: no negotiation", m,
                    {p.unique_id: "Passenger P", bus_agent.unique_id: "Bus (line H1)"},
                    until=lambda mod: mod.passengers[0].status == COMPLETED,
                    note="0 messages: buses follow fixed lines")


SCENARIOS = [rejection, sharing, walking, patience, bus]


def all_logs():
    return [make() for make in SCENARIOS]


if __name__ == "__main__":
    LOGS.mkdir(parents=True, exist_ok=True)
    for log in all_logs():
        (LOGS / f"{log['name']}.json").write_text(json.dumps(log, indent=1))
        labels = {lane["id"]: lane["label"] for lane in log["lanes"]}
        print(f"== {log['title']}: {len(log['messages'])} messages")
        for m in log["messages"]:
            print(f"  min {m['minute']:2d}  {labels[m['sender']]:>13} -> "
                  f"{labels[m['receiver']]:<13} {m['type']:8s} {m['data']}")
        for e in log["events"]:
            print(f"  min {e['minute']:2d}  event {labels[e['agent']]}: {e['text']}")
