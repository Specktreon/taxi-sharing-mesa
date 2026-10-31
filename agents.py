"""Taxi and passenger agents (genuine Mesa agents)."""

import mesa

from config import BOOKINGS_PER_SEAT
from messages import ACCEPT, CONFIRM, PROPOSE, REJECT, REQUEST, Message
from routing import grid_path, manhattan, step_towards

# Passenger statuses
WAITING = "waiting"  # requested a taxi, no taxi confirmed yet
ASSIGNED = "assigned"  # a taxi confirmed and is coming
TRAVELLING = "travelling"  # inside a taxi (including while boarding/alighting)
COMPLETED = "completed"  # reached destination within the simulation
NOT_COMPLETED = "not_completed"  # still waiting/assigned/travelling at the deadline
ABANDONED = "abandoned"  # gave up waiting for a CONFIRM (patience exceeded)

# Taxi states
IDLE = "idle"
TO_PICKUP = "to_pickup"  # driving towards the next pickup
CARRYING = "travelling"  # driving towards the next drop-off
PICKING_UP = "picking_up"  # stopped: a passenger is boarding
DROPPING_OFF = "dropping_off"  # stopped: a passenger is alighting

PICKUP = "pickup"
DROPOFF = "dropoff"

# Passenger travel modes (chosen once, at creation)
TAXI = "taxi"
BUS = "bus"
# Stages of a bus journey (status stays WAITING until boarding, TRAVELLING after)
TO_STOP, AT_STOP, RIDING, TO_DESTINATION = "to_stop", "at_stop", "riding", "to_destination"


def stop_district(stop):
    """District where a (kind, passenger) stop takes place."""
    kind, passenger = stop
    return passenger.pickup_district if kind == PICKUP else passenger.destination


class PassengerAgent(mesa.Agent):
    """A passenger who requests one trip from origin to destination.

    Timing (see metrics.py): pickup_time = minute the taxi reaches the pickup
    district (boarding starts); arrival_time = minute alighting at the
    destination ends. The pickup district is the origin, or with walking an
    adjacent district the passenger walks to after its CONFIRM.

    A bus passenger (mode BUS, see buses.py) walks to its boarding stop, waits,
    rides, then walks to its destination: pickup_time = boarding minute,
    alight_time = end of alighting, arrival_time = end of the final walk. It
    never contacts taxis and has no patience.
    """

    def __init__(self, model, origin, destination, request_time, patience=None,
                 bus_trip=None):
        super().__init__(model)
        self.origin = origin
        self.destination = destination
        self.mode = TAXI if bus_trip is None else BUS
        self.bus_line, self.board_stop, self.alight_stop = bus_trip or (None,) * 3
        self.bus_stage = None if bus_trip is None else TO_STOP
        self.bus = None
        self.alight_time = None
        self.pickup_district = origin
        self.walk_progress = 0  # minutes walked towards the next district
        self.request_time = request_time
        self.patience = patience  # minutes before abandoning; None = never
        self.pickup_time = None
        self.arrival_time = None
        self.abandon_time = None
        self.promised_pickup = None  # estimated pickup time given in CONFIRM
        self.status = WAITING
        self.status_at_deadline = None  # last active status if NOT_COMPLETED
        self.taxi = None
        self.shared = False  # True if another passenger rode with them
        self.ride_distance = 0  # districts driven while on board
        self.inbox = []
        self._individual = {}  # pickup district -> individual time

    @property
    def individual_time(self):
        """Baseline: boarding + direct x-first drive (with congestion costs)
        from the pickup district + alighting, alone, without waiting. A solo
        direct trip therefore has extra delay 0. Measured from the pickup
        district, so walking (the passenger's choice) is not extra delay.
        None for bus passengers (no direct-ride baseline)."""
        if self.mode == BUS:
            return None
        district = self.pickup_district
        if district not in self._individual:
            self._individual[district] = (
                self.model.travel_time(district, self.destination)
                + 2 * self.model.boarding_minutes
            )
        return self._individual[district]

    @property
    def walk_minutes(self):
        """Minutes of walking in the trip: origin -> pickup district for a
        taxi passenger; origin -> boarding stop plus alighting stop ->
        destination for a bus passenger."""
        if self.mode == BUS:
            districts = (manhattan(self.origin, self.board_stop)
                         + manhattan(self.alight_stop, self.destination))
        else:
            districts = manhattan(self.origin, self.pickup_district)
        return districts * self.model.walk_minutes_per_district

    @property
    def walking(self):
        """Confirmed and still on the way to another pickup district."""
        return self.status == ASSIGNED and self.pos != self.pickup_district

    # --- Derived times (None when not applicable) ---
    @property
    def waiting_time(self):
        """Minutes from request to pickup."""
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.request_time

    @property
    def in_vehicle_time(self):
        """Minutes from pickup (boarding starts) to the end of alighting (for
        a taxi passenger that is the arrival)."""
        if self.arrival_time is None:
            return None
        end = self.alight_time if self.mode == BUS else self.arrival_time
        return end - self.pickup_time

    @property
    def total_time(self):
        """Minutes from request to arrival (waiting + in-vehicle)."""
        if self.arrival_time is None:
            return None
        return self.arrival_time - self.request_time

    @property
    def extra_delay(self):
        """Actual in-vehicle time minus the individual trip time (taxi only)."""
        if self.arrival_time is None or self.mode == BUS:
            return None
        return self.in_vehicle_time - self.individual_time

    # --- Messaging phases (called by the model through AgentSet.do) ---
    def send_requests(self):
        """Phase 1: broadcast a call for proposals to every taxi."""
        if self.status != WAITING or self.mode != TAXI:
            return
        for taxi in self.model.taxis:
            self.model.send(
                Message(
                    self.unique_id,
                    taxi.unique_id,
                    REQUEST,
                    {"origin": self.origin, "destination": self.destination},
                    self.model.minute,
                )
            )

    def choose_taxi(self):
        """Phase 3: accept the proposal with the lowest estimated pickup time.

        With patience, proposals whose pickup would come after the patience
        runs out are ignored; with none left the passenger keeps waiting."""
        proposals = [
            m for m in self.inbox if m.type == PROPOSE and m.data["can_accept"]
        ]
        self.inbox.clear()
        if self.patience is not None:
            deadline = self.request_time + self.patience
            proposals = [m for m in proposals
                         if self.model.minute + m.data["eta"] <= deadline]
        if self.status != WAITING or not proposals:
            return
        # Ties broken by taxi id so runs are deterministic.
        best = min(proposals, key=lambda m: (m.data["eta"], m.sender))
        self.model.send(
            Message(self.unique_id, best.sender, ACCEPT, {}, self.model.minute)
        )

    def read_replies(self):
        """Phase 5: become ASSIGNED on CONFIRM; on REJECT retry next minute."""
        for m in self.inbox:
            if m.type == CONFIRM:
                self.status = ASSIGNED
                self.taxi = self.model.agent_by_id[m.sender]
                self.promised_pickup = m.data["pickup_time"]
                self.pickup_district = m.data["pickup_district"]
        self.inbox.clear()

    def walk(self):
        """Phase 5b: walk one minute, one district per
        walk_minutes_per_district (no congestion). A confirmed taxi passenger
        walks to its neighbouring pickup district (taxis only offer pickups the
        walker reaches first); a bus passenger walks to its boarding stop, or
        from its alighting stop to its destination."""
        if self.mode == BUS:
            target = {TO_STOP: self.board_stop,
                      TO_DESTINATION: self.destination}.get(self.bus_stage)
        else:
            target = self.pickup_district if self.walking else None
        if target is None:
            return
        self.walk_progress += 1
        if self.walk_progress >= self.model.walk_minutes_per_district:
            self.walk_progress = 0
            self.model.grid.move_agent(self, step_towards(self.pos, target))
            if self.mode == BUS and self.pos == target:
                self.reach_bus_target(self.model.minute + 1)

    # --- Bus journey ---
    def reach_bus_target(self, minute):
        """At the boarding stop: queue there. At the destination: done."""
        if self.bus_stage == TO_STOP:
            self.bus_stage = AT_STOP
            self.bus_line.waiting[self.board_stop].append(self)
        else:
            self.alight(minute)

    def board_bus(self, bus, minute):
        self.status = TRAVELLING
        self.bus_stage = RIDING
        self.bus = bus
        self.pickup_time = minute

    def leave_bus(self, minute):
        """Alighting finished: walk on to the destination (if not there)."""
        self.alight_time = minute
        self.bus_stage = TO_DESTINATION
        if self.pos == self.destination:
            self.alight(minute)

    # --- Events triggered by the taxi ---
    def board(self, taxi, minute):
        self.status = TRAVELLING
        self.pickup_time = minute

    def alight(self, minute):
        """Trip finished (taxi drop-off, or a bus passenger's final walk)."""
        self.status = COMPLETED
        self.bus_stage = None
        self.arrival_time = minute
        self.model.grid.remove_agent(self)

    def abandon(self, minute):
        """Give up waiting. Only called while WAITING, so no taxi holds a stop
        for this passenger (stops are added together with the CONFIRM)."""
        self.status = ABANDONED
        self.abandon_time = minute
        self.model.grid.remove_agent(self)


class TaxiAgent(mesa.Agent):
    """A taxi with a capacity, passengers on board and an ordered stop list."""

    def __init__(self, model, capacity):
        super().__init__(model)
        self.capacity = capacity
        self.onboard = []  # passengers currently in the taxi
        self.stops = []  # ordered planned stops: (PICKUP|DROPOFF, passenger)
        self.current_stop = None  # stop being served while dwelling
        self.dwell = 0  # boarding/alighting minutes left at the current stop
        self.promised_pickup = {}  # assigned passenger -> pickup time promised
        self.state = IDLE
        self.distance = 0  # districts travelled
        self.empty_distance = 0  # districts travelled with nobody on board
        self.occupied_distance = 0  # districts travelled with >= 1 passenger
        self.progress = 0  # minutes spent towards the next cell
        self.busy_minutes = 0  # minutes with a planned stop or a dwell
        self.occupied_minutes = 0  # minutes with at least one passenger on board
        self.inbox = []

    # --- Route planning ---
    def route_cells(self, stops=None):
        """Cells the taxi will drive through, starting with its position."""
        stops = self.stops if stops is None else stops
        cells = [self.pos]
        current = self.pos
        for stop in stops:
            district = stop_district(stop)
            cells += grid_path(current, district)
            current = district
        return cells

    def evaluate(self, stops):
        """Check a candidate stop list and estimate its timing.

        Returns (pickup_times, finish_time) or None if the plan
          - picks someone up twice or drops someone off before pickup,
          - exceeds the capacity at any point,
          - gives any passenger more than MAX extra in-vehicle delay, or
          - delays an assigned passenger's pickup more than MAX minutes past
            the time promised in their CONFIRM.
        Estimates: travel = model.travel_time (cost of every district entered
        on the x-first path), plus boarding_minutes at every stop. The taxi
        starts from its cell once the stop it is serving is finished; minutes
        already driven towards the next cell (progress) are credited on the
        first district entered, as in move(). Estimates are therefore exact.
        """
        model = self.model
        boarding = model.boarding_minutes
        t = model.minute + self.dwell
        position = self.pos
        credit = self.progress
        alighting = None
        if self.dwell and self.current_stop[0] == DROPOFF:
            alighting = self.current_stop[1]
        load = len(self.onboard) - (alighting is not None)
        pickup_times = {p: p.pickup_time for p in self.onboard if p is not alighting}
        for kind, passenger in stops:
            district = stop_district((kind, passenger))
            if district != position:
                t += model.travel_time(position, district)
                if credit:
                    # Entering the first cell takes at least one more minute.
                    first = model.cell_minutes[step_towards(position, district)]
                    t -= min(credit, first - 1)
                    credit = 0
            position = district
            if kind == PICKUP:
                if passenger in pickup_times:
                    return None
                promised = self.promised_pickup.get(passenger)
                if promised is not None and t - promised > model.max_extra_delay:
                    return None
                pickup_times[passenger] = t
                load += 1
                if load > self.capacity:
                    return None
                t += boarding
            else:
                if passenger not in pickup_times:
                    return None  # drop-off before pickup
                t += boarding
                load -= 1
                extra = (t - pickup_times[passenger]) - passenger.individual_time
                if extra > model.max_extra_delay:
                    return None
        return pickup_times, t

    def candidate_plans(self, passenger):
        """Stop lists that would serve the new passenger, depending on mode.

        "detour": general insertion, but a taxi takes on at most
        BOOKINGS_PER_SEAT * capacity passengers at a time (on board +
        assigned). This keeps stop lists short and avoids promising pickups
        far in the future."""
        mode = self.model.sharing_mode
        if mode == "detour":
            if self.committed() >= BOOKINGS_PER_SEAT * self.capacity:
                return []
            return self.insertions(passenger)
        if not self.stops:
            return [[(PICKUP, passenger), (DROPOFF, passenger)]]
        if mode == "no_detour":
            on_route = self.insert_on_route(passenger)
            if on_route is not None:
                return [on_route]
        return []

    def committed(self):
        """Passengers the taxi is responsible for: on board (except one who is
        already alighting) plus assigned and not yet picked up."""
        alighting = self.dwell > 0 and self.current_stop[0] == DROPOFF
        pending = sum(1 for kind, _ in self.stops if kind == PICKUP)
        return len(self.onboard) - alighting + pending

    def insertions(self, passenger):
        """Stages 3-4: insert the pickup at position i and the drop-off at
        position j >= i of the current stop list, for every (i, j); existing
        stops keep their order. With n stops this is (n+1)(n+2)/2 plans, each
        checked in O(n) by evaluate(). The booking limit (candidate_plans)
        keeps n <= 2 * (2 * capacity - 1) = 14 for capacity 4, i.e. at most
        120 plans: brute force is cheap enough here."""
        pickup = (PICKUP, passenger)
        dropoff = (DROPOFF, passenger)
        stops = self.stops
        n = len(stops)
        return [
            stops[:i] + [pickup] + stops[i:j] + [dropoff] + stops[j:]
            for i in range(n + 1)
            for j in range(i, n + 1)
        ]

    def insert_on_route(self, passenger):
        """Stage 2 rule: insert stops only if both districts lie, in order, on
        the current planned route. The driven route does not change."""
        cells = self.route_cells()
        if passenger.pickup_district not in cells:
            return None
        i_origin = cells.index(passenger.pickup_district)
        later = cells[i_origin + 1 :]
        if passenger.destination not in later:
            return None
        i_dest = i_origin + 1 + later.index(passenger.destination)
        # Route index at which each existing stop is reached.
        stop_index = []
        index = 0
        current = self.pos
        for stop in self.stops:
            district = stop_district(stop)
            index += len(grid_path(current, district))
            current = district
            stop_index.append(index)
        n_before_pickup = sum(1 for i in stop_index if i <= i_origin)
        n_before_drop = sum(1 for i in stop_index if i < i_dest)
        return (
            self.stops[:n_before_pickup]
            + [(PICKUP, passenger)]
            + self.stops[n_before_pickup:n_before_drop]
            + [(DROPOFF, passenger)]
            + self.stops[n_before_drop:]
        )

    def pickup_districts(self, passenger):
        """The origin and, with walk_radius 1, each adjacent district inside
        the grid (except the destination: no walking the whole trip)."""
        districts = [passenger.origin]
        if self.model.walk_radius:
            x, y = passenger.origin
            for cell in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (0 <= cell[0] < self.model.width and 0 <= cell[1] < self.model.height
                        and cell != passenger.destination):
                    districts.append(cell)
        return districts

    def best_plan(self, passenger):
        """Feasible plan with the earliest pickup; ties: earliest finish, then
        no walking. A walking pickup must be reachable on foot (walking starts
        at the CONFIRM, this minute) no later than the taxi gets there.

        The passenger is WAITING, so no stop list holds it yet: its
        pickup_district can be set per candidate and is restored afterwards.
        Returns (stops, estimated pickup minute, pickup district) or None."""
        best = None
        try:
            for district in self.pickup_districts(passenger):
                passenger.pickup_district = district
                walk_done = self.model.minute + passenger.walk_minutes
                walked = district != passenger.origin
                for stops in self.candidate_plans(passenger):
                    result = self.evaluate(stops)
                    if result is None:
                        continue
                    pickup_times, finish = result
                    if walked and pickup_times[passenger] < walk_done:
                        continue  # the taxi would have to wait for the walker
                    key = (pickup_times[passenger], finish, walked)
                    if best is None or key < best[0]:
                        best = (key, stops, district)
        finally:
            passenger.pickup_district = passenger.origin
        if best is None:
            return None
        (pickup_time, _, _), stops, district = best
        return stops, pickup_time, district

    # --- Messaging phases ---
    def handle_requests(self):
        """Phase 2: answer each REQUEST with a PROPOSE (eta, can_accept)."""
        requests = [m for m in self.inbox if m.type == REQUEST]
        self.inbox.clear()
        for m in requests:
            passenger = self.model.agent_by_id[m.sender]
            plan = self.best_plan(passenger)
            self.model.send(
                Message(
                    self.unique_id,
                    m.sender,
                    PROPOSE,
                    {
                        "can_accept": plan is not None,
                        "eta": None if plan is None else plan[1] - self.model.minute,
                        "pickup_district": None if plan is None else plan[2],
                    },
                    self.model.minute,
                )
            )

    def handle_accepts(self):
        """Phase 4: re-check feasibility (the plan may have changed since the
        proposal), then CONFIRM with the promised pickup time and adopt the
        new stops, or REJECT."""
        accepts = sorted(
            (m for m in self.inbox if m.type == ACCEPT), key=lambda m: m.sender
        )
        self.inbox.clear()
        for m in accepts:
            passenger = self.model.agent_by_id[m.sender]
            plan = self.best_plan(passenger)
            if plan is not None and passenger.status == WAITING:
                self.stops, pickup_time, district = plan
                # Recorded here (not when the passenger reads the CONFIRM) so
                # later ACCEPTs in this same phase already respect them: the
                # new stops refer to the agreed pickup district.
                self.promised_pickup[passenger] = pickup_time
                passenger.pickup_district = district
                reply, data = CONFIRM, {"pickup_time": pickup_time,
                                        "pickup_district": district}
            else:
                reply, data = REJECT, {}
            self.model.send(
                Message(self.unique_id, m.sender, reply, data, self.model.minute)
            )
        self.update_state()

    # --- Movement ---
    def serve_stops(self, minute):
        """Start every stop located at the current cell, one after the other.

        A stop takes boarding_minutes: pickups board at the start of the dwell,
        drop-offs alight at its end. With 0 minutes the stop is instantaneous.
        """
        while self.dwell == 0 and self.stops and stop_district(self.stops[0]) == self.pos:
            stop = self.stops.pop(0)
            kind, passenger = stop
            if kind == PICKUP:
                passenger.board(self, minute)
                self.onboard.append(passenger)
                self.promised_pickup.pop(passenger, None)
                self.state = PICKING_UP
            else:
                self.state = DROPPING_OFF
            self.current_stop = stop
            self.dwell = self.model.boarding_minutes
            if self.dwell == 0:
                self.finish_stop(minute)

    def finish_stop(self, minute):
        kind, passenger = self.current_stop
        if kind == DROPOFF:
            self.onboard.remove(passenger)
            passenger.alight(minute)
        self.current_stop = None

    def count_minute(self):
        """Bookkeeping for a minute spent driving or dwelling."""
        self.busy_minutes += 1
        if self.onboard:
            self.occupied_minutes += 1
        if len(self.onboard) >= 2:
            for p in self.onboard:
                p.shared = True

    def move(self):
        """Phase 6: spend one minute boarding/alighting or driving towards the
        next cell on the route; the taxi enters it once progress reaches that
        cell's cell_minutes (no teleporting)."""
        now = self.model.minute
        self.update_state()
        self.serve_stops(now)
        if self.dwell > 0:
            self.count_minute()
            self.dwell -= 1
            if self.dwell == 0:
                self.finish_stop(now + 1)
                self.update_state()
                self.serve_stops(now + 1)
            return
        if self.stops:
            self.count_minute()
            self.progress += 1
            new_pos = step_towards(self.pos, stop_district(self.stops[0]))
            if self.progress >= self.model.cell_minutes[new_pos]:
                self.progress = 0
                self.model.grid.move_agent(self, new_pos)
                for p in self.onboard:
                    self.model.grid.move_agent(p, new_pos)
                    p.ride_distance += 1
                self.distance += 1
                if self.onboard:
                    self.occupied_distance += 1
                else:
                    self.empty_distance += 1
                if self.state in (PICKING_UP, DROPPING_OFF):
                    self.update_state()
                self.serve_stops(now + 1)

    def update_state(self):
        if self.dwell > 0:
            return  # keep PICKING_UP / DROPPING_OFF while dwelling
        if not self.stops:
            self.state = IDLE
        elif self.stops[0][0] == PICKUP:
            self.state = TO_PICKUP
        else:
            self.state = CARRYING
