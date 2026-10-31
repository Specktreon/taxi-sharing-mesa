"""Metric definitions shared by the model, the interface and the experiments.

Timing (all in simulated minutes; b = boarding_minutes, at every stop):
    pickup_time      = minute the taxi reaches the origin (boarding starts)
    arrival_time     = minute alighting at the destination ends
    individual time  = 2*b + travel time of the direct x-first path
                       (board, drive it alone, alight); the travel time sums
                       minutes_per_district x congestion factor per district
    waiting time     = pickup - request
    in-vehicle time  = arrival - pickup  (includes own boarding/alighting and
                       any detours and other passengers' stops)
    total time       = arrival - request  (waiting + in-vehicle)
    extra delay      = in-vehicle time - individual time  (0 for a solo,
                       direct trip; > 0 only because of sharing)
Averages marked "completed" only include passengers who reached their
destination; the matching count is always reported next to them.
"wait_censored" includes every created passenger: unserved passengers count
the time they had waited when the simulation ended (a lower bound); abandoned
passengers count the time until they gave up.

Acceptability (optional patience model): a passenger still waiting for a
CONFIRM after their patience abandons; abandoned passengers are not
not_completed. acceptable_pct = % of created passengers who completed with
waiting time <= their patience (any wait when patience is disabled) and extra
delay <= the model's max_extra_delay (MAX_EXTRA_DELAY_MINUTES).

Walking (optional): a passenger picked up in a neighbouring district has its
individual time and extra delay measured from that pickup district; its
waiting time (pickup - request) includes the walk. walked_pct = % of
completed passengers who walked; avg_walk_minutes = mean walking minutes over
completed passengers (0 for those who did not walk).

Distances are counted in districts driven. total = empty + occupied, where
"empty" means no passenger on board. passenger_distance sums, over passengers,
the districts each one rode (passenger-km); avg_occupancy =
passenger_distance / total_distance (passengers per driven district). These
are simple proxies for vehicle travel, not measured pollution or congestion.
"""

import math

from agents import (ABANDONED, ASSIGNED, COMPLETED, NOT_COMPLETED, TRAVELLING,
                    WAITING)

MODEL_METRICS = [
    "minute",
    "created",
    "waiting",
    "assigned",
    "travelling",
    "completed",
    "not_completed",
    "abandoned",
    "completed_pct",
    "abandoned_pct",
    "acceptable_pct",
    "avg_wait_completed",
    "avg_in_vehicle_completed",
    "avg_total_completed",
    "avg_extra_delay_completed",
    "shared_completed",
    "avg_extra_delay_shared",
    "max_extra_delay",
    "avg_wait_censored",
    "walked_pct",
    "avg_walk_minutes",
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
    "pickup_district": lambda p: f"{p.pickup_district[0]};{p.pickup_district[1]}",
    "walk_minutes": "walk_minutes",
    "request_time": "request_time",
    "patience": "patience",
    "promised_pickup": "promised_pickup",
    "pickup_time": "pickup_time",
    "arrival_time": "arrival_time",
    "abandon_time": "abandon_time",
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
        if p.abandon_time is not None:
            return p.abandon_time - p.request_time
        return model.minute - p.request_time

    acceptable = [
        p for p in done
        if (p.patience is None or p.waiting_time <= p.patience)
        and p.extra_delay <= model.max_extra_delay
    ]
    abandoned = status.count(ABANDONED)

    return {
        "minute": model.minute,
        "created": created,
        "waiting": status.count(WAITING),
        "assigned": status.count(ASSIGNED),
        "travelling": status.count(TRAVELLING),
        "completed": len(done),
        "not_completed": status.count(NOT_COMPLETED),
        "abandoned": abandoned,
        "completed_pct": 100 * len(done) / created if created else math.nan,
        "abandoned_pct": 100 * abandoned / created if created else math.nan,
        "acceptable_pct": (
            100 * len(acceptable) / created if created else math.nan
        ),
        "avg_wait_completed": mean(p.waiting_time for p in done),
        "avg_in_vehicle_completed": mean(p.in_vehicle_time for p in done),
        "avg_total_completed": mean(p.total_time for p in done),
        "avg_extra_delay_completed": mean(p.extra_delay for p in done),
        "shared_completed": len(shared_done),
        "avg_extra_delay_shared": mean(p.extra_delay for p in shared_done),
        "max_extra_delay": max((p.extra_delay for p in done), default=math.nan),
        "avg_wait_censored": mean(censored_wait(p) for p in passengers),
        "walked_pct": (
            100 * sum(p.pickup_district != p.origin for p in done) / len(done)
            if done else math.nan
        ),
        "avg_walk_minutes": mean(p.walk_minutes for p in done),
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
