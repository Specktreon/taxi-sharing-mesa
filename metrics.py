"""Metric definitions shared by the model, the interface and the experiments.

Timing (all in simulated minutes; b = boarding_minutes, at every stop):
    pickup_time      = minute the taxi reaches the origin (boarding starts)
    arrival_time     = minute alighting at the destination ends
    individual time  = 2*b + direct distance * minutes_per_district
                       (board, drive the shortest path alone, alight)
    waiting time     = pickup - request
    in-vehicle time  = arrival - pickup  (includes own boarding/alighting and
                       any detours and other passengers' stops)
    total time       = arrival - request  (waiting + in-vehicle)
    extra delay      = in-vehicle time - individual time  (0 for a solo,
                       direct trip; > 0 only because of sharing)
Averages marked "completed" only include passengers who reached their
destination; the matching count is always reported next to them.
"wait_censored" includes every created passenger: unserved passengers count
the time they had waited when the simulation ended (a lower bound).

Distances are counted in districts driven. total = empty + occupied, where
"empty" means no passenger on board. passenger_distance sums, over passengers,
the districts each one rode (passenger-km); avg_occupancy =
passenger_distance / total_distance (passengers per driven district). These
are simple proxies for vehicle travel, not measured pollution or congestion.
"""

import math

from agents import ASSIGNED, COMPLETED, NOT_COMPLETED, TRAVELLING, WAITING

MODEL_METRICS = [
    "minute",
    "created",
    "waiting",
    "assigned",
    "travelling",
    "completed",
    "not_completed",
    "completed_pct",
    "avg_wait_completed",
    "avg_in_vehicle_completed",
    "avg_total_completed",
    "avg_extra_delay_completed",
    "shared_completed",
    "avg_extra_delay_shared",
    "max_extra_delay",
    "avg_wait_censored",
    "total_distance",
    "empty_distance",
    "occupied_distance",
    "empty_distance_pct",
    "passenger_distance",
    "avg_occupancy",
    "distance_per_completed",
    "utilization_pct",
    "busy_pct",
    "messages",
]

PASSENGER_REPORTERS = {
    "passenger_id": "unique_id",
    "origin": lambda p: f"{p.origin[0]};{p.origin[1]}",
    "destination": lambda p: f"{p.destination[0]};{p.destination[1]}",
    "request_time": "request_time",
    "promised_pickup": "promised_pickup",
    "pickup_time": "pickup_time",
    "arrival_time": "arrival_time",
    "status": "status",
    "status_at_deadline": "status_at_deadline",
    "taxi_id": lambda p: None if p.taxi is None else p.taxi.unique_id,
    "shared": "shared",
    "individual_time": "individual_time",
    "waiting_time": "waiting_time",
    "in_vehicle_time": "in_vehicle_time",
    "total_time": "total_time",
    "extra_delay": "extra_delay",
    "ride_distance": "ride_distance",
}


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else math.nan


def compute(model):
    passengers = model.passengers
    status = [p.status for p in passengers]
    done = [p for p in passengers if p.status == COMPLETED]
    shared_done = [p for p in done if p.shared]
    created = len(passengers)
    taxi_minutes = len(model.taxis) * model.minute
    total_distance = sum(t.distance for t in model.taxis)
    empty_distance = sum(t.empty_distance for t in model.taxis)
    passenger_distance = sum(p.ride_distance for p in passengers)

    def censored_wait(p):
        if p.pickup_time is not None:
            return p.waiting_time
        return model.minute - p.request_time

    return {
        "minute": model.minute,
        "created": created,
        "waiting": status.count(WAITING),
        "assigned": status.count(ASSIGNED),
        "travelling": status.count(TRAVELLING),
        "completed": len(done),
        "not_completed": status.count(NOT_COMPLETED),
        "completed_pct": 100 * len(done) / created if created else math.nan,
        "avg_wait_completed": mean(p.waiting_time for p in done),
        "avg_in_vehicle_completed": mean(p.in_vehicle_time for p in done),
        "avg_total_completed": mean(p.total_time for p in done),
        "avg_extra_delay_completed": mean(p.extra_delay for p in done),
        "shared_completed": len(shared_done),
        "avg_extra_delay_shared": mean(p.extra_delay for p in shared_done),
        "max_extra_delay": max((p.extra_delay for p in done), default=math.nan),
        "avg_wait_censored": mean(censored_wait(p) for p in passengers),
        "total_distance": total_distance,
        "empty_distance": empty_distance,
        "occupied_distance": sum(t.occupied_distance for t in model.taxis),
        "empty_distance_pct": (
            100 * empty_distance / total_distance if total_distance else math.nan
        ),
        "passenger_distance": passenger_distance,
        "avg_occupancy": (
            passenger_distance / total_distance if total_distance else math.nan
        ),
        "distance_per_completed": total_distance / len(done) if done else math.nan,
        "utilization_pct": (
            100 * sum(t.occupied_minutes for t in model.taxis) / taxi_minutes
            if taxi_minutes else math.nan
        ),
        "busy_pct": (
            100 * sum(t.busy_minutes for t in model.taxis) / taxi_minutes
            if taxi_minutes else math.nan
        ),
        "messages": sum(model.message_counts.values()),
    }
