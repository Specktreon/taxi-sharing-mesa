"""Simulation constants and default parameters.

One simulation step = one simulated minute. The study uses FIXED settings: a
30x30 city, 120 minutes, gradual requests over the first 90 minutes, 1 minute
per district, 1 boarding minute per stop, MAX_EXTRA_DELAY_MINUTES = 10, and,
when the features are switched on, patience 10-30 min, walking 3 min per
district and the bus settings below. Only the sharing mode, taxi capacity,
fleet size, demand, seed and the four features (buses, walking, congestion,
patience: see FEATURES) vary between scenarios.
"""

# Maximum additional in-vehicle time (minutes) any passenger may suffer because
# of sharing. Kept FIXED across all experiments so results stay comparable.
MAX_EXTRA_DELAY_MINUTES = 10

# Taxi speed: minutes needed to cross one district (grid cell).
MINUTES_PER_DISTRICT = 1

# Dwell time at every pickup and every drop-off: the taxi stays in the
# district this many minutes before driving on (0 = instantaneous stops).
BOARDING_MINUTES = 1

# Passenger patience (minutes): each passenger draws an integer patience
# uniformly in [PATIENCE_MIN, PATIENCE_MAX] and abandons if still waiting for a
# CONFIRM after that long. PATIENCE_MAX = None (or 0) disables abandonment;
# the "patience" feature switches it on with PATIENCE_MAX_ON.
PATIENCE_MIN = 10
PATIENCE_MAX = None
PATIENCE_MAX_ON = 30

# Traffic congestion (parameter `congestion`):
#   "off"    every district costs minutes_per_district to enter.
#   "center" a central rectangle of (width // CONGESTION_CENTER_FRACTION) x
#            (height // CONGESTION_CENTER_FRACTION) districts (10x10 on 30x30)
#            costs CENTER_FACTOR times that, the ring of districts around it
#            RING_FACTOR times; all others factor 1.
CONGESTION_MODES = ("off", "center")
CONGESTION_CENTER_FRACTION = 3
CENTER_FACTOR = 3
RING_FACTOR = 2

# Walking to a neighbouring district (parameter walk_radius): 0 = off; 1 = a
# taxi may also pick the passenger up in an adjacent district (Manhattan
# distance 1) that the passenger can reach before the taxi. Walking speed is
# not affected by congestion.
WALK_RADII = (0, 1)
WALK_MINUTES_PER_DISTRICT = 3

# Buses (parameter `buses`, default off): three horizontal lines (rows h//4,
# h//2 and 3h//4) and three vertical lines (columns w//4, w//2 and 3w//4: 7,
# 15 and 22 on 30x30), driven back and forth at taxi speed (congestion
# applies). Stops every BUS_STOP_SPACING districts, including both ends. A
# passenger takes the bus when its trip is at least BUS_MIN_TRIP districts long
# (Manhattan distance) and one line has a stop within BUS_WALK_MAX districts of
# its origin and a different stop within BUS_WALK_MAX of its destination (no
# transfers); otherwise it calls a taxi.
BUSES_PER_LINE = 2
BUS_CAPACITY = 10
BUS_STOP_SPACING = 3
BUS_WALK_MAX = 3
BUS_MIN_TRIP = 6

# Allowed taxi capacities (seats).
CAPACITIES = (1, 2, 3, 4)

# "detour" mode: a taxi takes on at most BOOKINGS_PER_SEAT * capacity
# passengers at a time (on board + assigned, not yet picked up). It can book
# its next riders ahead while still sharing, and its stop list stays short
# (<= 4 * capacity stops), so the brute-force insertion search stays cheap.
BOOKINGS_PER_SEAT = 2

# Sharing modes, matching the incremental stages of the project:
#   "none"      Stage 1: a taxi serves one passenger at a time.
#   "no_detour" Stage 2: a second passenger is accepted only if the trip lies
#               on the taxi's already planned route (route does not change).
#   "detour"    Stages 3-4: the new pickup and drop-off may be inserted at any
#               positions of the taxi's stop list (route changes, several
#               stops, up to `capacity` passengers) as long as no passenger
#               exceeds MAX_EXTRA_DELAY_MINUTES of extra in-vehicle time and no
#               assigned passenger's pickup slips more than that past its
#               promised time.
SHARING_MODES = ("none", "no_detour", "detour")

# Passenger arrival modes:
#   "all_at_start" every passenger requests a taxi at minute 0.
#   "gradual"      request minutes are drawn uniformly in [0, arrival_window).
ARRIVAL_MODES = ("all_at_start", "gradual")

# Base scenario. num_taxis / num_passengers were calibrated so that sharing
# "none" with capacity 1 completes roughly 50-70 % of passengers (about 58 %
# over seeds 1-10); see README section 8.
DEFAULTS = {
    "width": 30,
    "height": 30,
    "num_taxis": 20,
    "num_passengers": 90,
    "capacity": 1,
    "sharing_mode": "none",
    "arrival_mode": "gradual",
    "arrival_window": 90,
    "duration": 120,
    "congestion": "off",
    "walk_radius": 0,
    "buses": False,
    "seed": 1,
}

# The four on/off features used by the sidebar and experiments.csv.
FEATURES = ("buses", "walking", "congestion", "patience")


def feature_params(buses=False, walking=False, congestion=False, patience=False):
    """TaxiModel keyword arguments for the four on/off features."""
    return {
        "buses": bool(buses),
        "walk_radius": 1 if walking else 0,
        "congestion": "center" if congestion else "off",
        "patience_min": PATIENCE_MIN,
        "patience_max": PATIENCE_MAX_ON if patience else None,
    }
