"""Simulation constants and default parameters.

One simulation step = one simulated minute.
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
# CONFIRM after that long. PATIENCE_MAX = None (or 0) disables abandonment.
PATIENCE_MIN = 10
PATIENCE_MAX = None

# Traffic congestion (parameter `congestion`):
#   "off"    every district costs minutes_per_district to enter.
#   "center" the central CONGESTION_CENTER_SIZE x CONGESTION_CENTER_SIZE
#            districts cost CENTER_FACTOR times that, the ring of districts
#            around them RING_FACTOR times; all others factor 1.
CONGESTION_MODES = ("off", "center")
CONGESTION_CENTER_SIZE = 6
CENTER_FACTOR = 3
RING_FACTOR = 2

# Walking to a neighbouring district (parameter walk_radius): 0 = off; 1 = a
# taxi may also pick the passenger up in an adjacent district (Manhattan
# distance 1) that the passenger can reach before the taxi. Walking speed is
# not affected by congestion.
WALK_RADII = (0, 1)
WALK_MINUTES_PER_DISTRICT = 3

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

DEFAULTS = {
    "width": 20,
    "height": 20,
    "num_taxis": 5,
    "num_passengers": 40,
    "capacity": 1,
    "sharing_mode": "none",
    "arrival_mode": "all_at_start",
    "arrival_window": 60,
    "duration": 60,
    "congestion": "off",
    "walk_radius": 0,
    "seed": 1,
}
