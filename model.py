"""TaxiModel: the Mesa model that runs the taxi-sharing simulation."""

import random
from collections import Counter

import mesa
from mesa.space import MultiGrid

import metrics
from agents import (
    ASSIGNED,
    NOT_COMPLETED,
    TRAVELLING,
    WAITING,
    PassengerAgent,
    TaxiAgent,
)
from config import (
    ARRIVAL_MODES,
    BOARDING_MINUTES,
    CAPACITIES,
    DEFAULTS,
    MAX_EXTRA_DELAY_MINUTES,
    MINUTES_PER_DISTRICT,
    SHARING_MODES,
)


def generate_scenario(seed, width, height, num_taxis, num_passengers, arrival_mode,
                      arrival_window):
    """Create taxi start cells and passenger requests from the seed only.

    Separate random generators are used for demand and fleet, so the same seed
    gives the same passengers whatever the capacity, sharing mode or fleet
    size (5 taxis are the first 5 of the 10-taxi fleet). The request minute is
    always drawn, so origins/destinations do not depend on the arrival mode.
    """
    demand_rng = random.Random(f"demand-{seed}")
    fleet_rng = random.Random(f"fleet-{seed}")

    def random_cell(rng):
        return (rng.randrange(width), rng.randrange(height))

    requests = []
    for _ in range(num_passengers):
        origin = random_cell(demand_rng)
        destination = random_cell(demand_rng)
        while destination == origin:
            destination = random_cell(demand_rng)
        minute = demand_rng.randrange(arrival_window)
        if arrival_mode == "all_at_start":
            minute = 0
        requests.append((minute, origin, destination))
    taxi_starts = [random_cell(fleet_rng) for _ in range(num_taxis)]
    return taxi_starts, requests


class TaxiModel(mesa.Model):
    """City grid with taxis and passengers. One step = one simulated minute.

    Step phases (each run through Mesa's AgentSet.do):
        0. passengers whose request minute has come are created
        1. waiting passengers send REQUEST to all taxis
        2. taxis answer with PROPOSE (estimated pickup time, can_accept)
        3. passengers send ACCEPT to the taxi with the lowest estimate
        4. taxis CONFIRM (and update their stops) or REJECT
        5. passengers read the replies
        6. taxis spend one minute driving one district or boarding/alighting
           (boarding_minutes at every pickup and drop-off)
        7. clock advances; at the deadline unfinished passengers are marked
           NOT_COMPLETED and the model stops; metrics are collected
    """

    def __init__(
        self,
        width=DEFAULTS["width"],
        height=DEFAULTS["height"],
        num_taxis=DEFAULTS["num_taxis"],
        num_passengers=DEFAULTS["num_passengers"],
        capacity=DEFAULTS["capacity"],
        sharing_mode=DEFAULTS["sharing_mode"],
        arrival_mode=DEFAULTS["arrival_mode"],
        arrival_window=DEFAULTS["arrival_window"],
        duration=DEFAULTS["duration"],
        minutes_per_district=MINUTES_PER_DISTRICT,
        boarding_minutes=BOARDING_MINUTES,
        max_extra_delay=MAX_EXTRA_DELAY_MINUTES,
        seed=DEFAULTS["seed"],
        taxi_starts=None,
        requests=None,
    ):
        """taxi_starts / requests allow hand-made deterministic scenarios:
        taxi_starts = [(x, y), ...], requests = [(minute, origin, dest), ...].
        When given, they replace the randomly generated ones."""
        super().__init__(rng=seed)
        if sharing_mode not in SHARING_MODES:
            raise ValueError(f"sharing_mode must be one of {SHARING_MODES}")
        if arrival_mode not in ARRIVAL_MODES:
            raise ValueError(f"arrival_mode must be one of {ARRIVAL_MODES}")
        if int(capacity) not in CAPACITIES:
            raise ValueError(f"capacity must be one of {CAPACITIES}")
        if duration < 1 or minutes_per_district < 1 or boarding_minutes < 0:
            raise ValueError("duration and minutes_per_district must be >= 1, "
                             "boarding_minutes >= 0")

        self.width = width
        self.height = height
        self.capacity = int(capacity)
        self.sharing_mode = sharing_mode
        self.arrival_mode = arrival_mode
        self.duration = int(duration)
        self.arrival_window = max(1, min(int(arrival_window), self.duration))
        self.minutes_per_district = minutes_per_district
        self.boarding_minutes = int(boarding_minutes)
        self.max_extra_delay = max_extra_delay
        self.seed = seed
        self.minute = 0
        self.message_counts = Counter()

        generated_starts, generated_requests = generate_scenario(
            seed, width, height, num_taxis, num_passengers, arrival_mode,
            self.arrival_window,
        )
        taxi_starts = generated_starts if taxi_starts is None else taxi_starts
        requests = generated_requests if requests is None else requests
        # Requests at or after the deadline could never be served; drop them.
        self.pending_requests = sorted(
            (r for r in requests if r[0] < self.duration), key=lambda r: r[0]
        )

        self.grid = MultiGrid(width, height, torus=False)
        self.agent_by_id = {}
        self.taxis = []
        self.passengers = []
        for cell in taxi_starts:
            taxi = TaxiAgent(self, self.capacity)
            self.grid.place_agent(taxi, cell)
            self.taxis.append(taxi)
            self.agent_by_id[taxi.unique_id] = taxi

        self.datacollector = mesa.DataCollector(
            model_reporters={
                key: (lambda m, key=key: m.latest_metrics[key])
                for key in metrics.MODEL_METRICS
            },
            agenttype_reporters={PassengerAgent: metrics.PASSENGER_REPORTERS},
        )
        self.spawn_due_passengers()
        self.running = True
        self.collect()

    # --- Messaging ---
    def send(self, message):
        """Deliver a message to the receiver's inbox."""
        self.agent_by_id[message.receiver].inbox.append(message)
        self.message_counts[message.type] += 1

    # --- Simulation loop ---
    def spawn_due_passengers(self):
        while self.pending_requests and self.pending_requests[0][0] <= self.minute:
            minute, origin, destination = self.pending_requests.pop(0)
            passenger = PassengerAgent(self, origin, destination, minute)
            self.grid.place_agent(passenger, origin)
            self.passengers.append(passenger)
            self.agent_by_id[passenger.unique_id] = passenger

    def step(self):
        if not self.running:
            return  # deadline already reached (UI may call step() again)
        self.spawn_due_passengers()
        passengers = self.agents_by_type.get(PassengerAgent)
        taxis = self.agents_by_type[TaxiAgent]
        if passengers is not None:
            passengers.do("send_requests")
            taxis.do("handle_requests")
            passengers.do("choose_taxi")
            taxis.do("handle_accepts")
            passengers.do("read_replies")
        taxis.do("move")

        self.minute += 1
        if self.minute >= self.duration:
            self.finish()
        self.collect()

    def finish(self):
        """Deadline reached: anyone not delivered is NOT_COMPLETED."""
        for p in self.passengers:
            if p.status in (WAITING, ASSIGNED, TRAVELLING):
                p.status_at_deadline = p.status
                p.status = NOT_COMPLETED
        self.running = False

    def collect(self):
        self.latest_metrics = metrics.compute(self)
        self.datacollector.collect(self)
