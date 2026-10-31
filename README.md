# Taxi-Sharing Multi-Agent Simulation (Mesa)

Master's project for *Foundations of Agent-Based Systems*.

**Research question:** How does taxi sharing affect the number of passengers
served, passenger waiting times, journey times, and taxi distance travelled
under different simulation configurations?

## 1. Installation

Requires Python 3.12+ (developed and tested with Python 3.14.6 and Mesa 3.5.1).

With Conda (recommended):

```powershell
conda create -n taxi-mesa "python=3.14.6=*_cp314" -y
conda activate taxi-mesa
python -m pip install -r requirements.txt
```

`*_cp314` selects the standard (not free-threaded) Python build.
Without Conda: create a virtual environment with Python 3.12+ and run
`python -m pip install -r requirements.txt`.

## 2. Running

All commands are run from the project folder.

| Task | Command |
|---|---|
| Interactive visualization | `python -m solara run app.py` then open http://localhost:8765 |
| All experiments (10 configs x 5 seeds) | `python run_experiments.py` |
| Selected configurations / seeds | `python run_experiments.py --only C3 C6 --seeds 1 2` |
| Tests | `python -m pytest` |

**Visualization.** The sidebar holds the controls: *Reset*, *Step*, and
▶ / ❚❚ (play/pause). It also holds the model parameters:

- grid width and height (10-40 districts each, default 20);
- number of taxis and number of passengers;
- capacity (1-4) and sharing mode;
- boarding time per stop;
- patience min and patience max (*Patience max* 0 = passengers never abandon;
  if min > max, the two are swapped on Reset);
- traffic congestion (`off` / `center`);
- *Walk to neighbour district* (on = `walk_radius` 1) and walking time per
  district;
- arrival mode and arrival window;
- duration and seed.

After changing a parameter, press *Reset* to rebuild the model. The simulation
stops by itself when the configured duration is reached. Each step redraws two
images, so Play runs at about 1-2 minutes per second. Raise *Render Interval*
to go faster.

The page shows:

- the city map (example: `docs/grid_example.png`);
- a status panel with the minute, configuration, and results table;
- a 2x2 chart panel over time: passengers by status, average times, taxi
  distance (total / occupied / empty), and taxi utilization.

The panels can be dragged and resized.

Map legend:

| Symbol | Meaning |
|---|---|
| grey square | idle taxi |
| orange square | taxi driving to a pickup |
| blue square | taxi driving to a drop-off |
| green square | taxi stopped, a passenger is boarding |
| purple square | taxi stopped, a passenger is alighting |
| `2/4` next to a taxi | passengers on board / seats |
| thin line | the taxi's planned route, in the taxi's colour |
| ▲ / ▼ | planned pickup / planned drop-off of that taxi |
| red dot | passenger waiting, no taxi yet |
| yellow dot | passenger waiting, a taxi is assigned |
| number in a dot | several passengers waiting in that district |
| black cross | passenger not completed at the deadline |
| brown ring | passenger abandoned (gave up waiting), at their origin |
| teal diamond + dashed arrow | passenger walking to a neighbouring pickup district (arrow points to it) |
| darker orange shade | congested centre, x3 (only with congestion on) |
| light orange shade | congestion ring, x2 (only with congestion on) |

**Experiments.** The configurations are listed in `experiments.csv`. Edit that
file to define new scenarios; the source code does not need to change. Results
are written to `results/`:

- `runs.csv`: one row per configuration and seed, with all metrics.
- `summary.csv`: mean and standard deviation over seeds for each configuration.
- `passengers.csv`: every passenger in every run, with times, status, and
  extra delay.
- `charts/*.png`: comparison bar charts. `comparison.png` shows all of them
  together.

`experiments.csv` may contain these optional columns. When a column is absent,
every run uses the default:

| Column | Default when absent |
|---|---|
| `boarding_minutes` | `BOARDING_MINUTES` from `config.py` (1) |
| `patience_min` | `PATIENCE_MIN` from `config.py` (10) |
| `patience_max` | empty: no abandonment (an empty cell or 0 also disables it for that row) |
| `congestion` | `off` (or `center`) |
| `walk_radius` | 0: no walking (or 1) |
| `walk_minutes_per_district` | `WALK_MINUTES_PER_DISTRICT` from `config.py` (3) |
| `width`, `height` | 20 x 20 districts |

**Troubleshooting.**

- **Blank main area** (only the sidebar is visible; the browser console shows
  `GlobalVue.use is not a function`): the widget packages are the Vue 3 lines
  (`ipyvue`/`ipyvuetify` 3.x). Mesa 3.5.1's dashboard needs the Vue 2 lines
  that `requirements.txt` pins. Run `python -m pip install -r requirements.txt`
  and restart the server.
- **DLL error:** if `solara run` fails with
`ImportError: DLL load failed while importing _imaging`, and the traceback shows
paths of another Python installation, the `VIRTUAL_ENV` environment variable
points to that installation. IPython then adds its packages to the search path.
Clear the variable for the session (PowerShell: `Remove-Item Env:VIRTUAL_ENV`)
and start again with `python -m solara run app.py`.

## 3. Files

| File | Content |
|---|---|
| `config.py` | Constants (`MAX_EXTRA_DELAY_MINUTES = 10`, `MINUTES_PER_DISTRICT = 1`, `BOARDING_MINUTES = 1`, `CAPACITIES`, `BOOKINGS_PER_SEAT = 2`) and defaults |
| `messages.py` | `Message` class and message types |
| `routing.py` | Manhattan distance, x-first grid path, congestion factors |
| `agents.py` | `TaxiAgent`, `PassengerAgent` (Mesa agents), route planning, sharing rules |
| `model.py` | `TaxiModel`: `MultiGrid`, demand generation, step phases, deadline, `DataCollector` |
| `metrics.py` | Metric definitions used by the model, the UI and the experiments |
| `app.py` | Mesa `SolaraViz` interface: city map (`draw_city`), status panel, charts |
| `run_experiments.py` | Experiment runner (Mesa `batch_run`), CSV export, charts |
| `experiments.csv` | The 10 experiment configurations |
| `tests/` | Pytest test suite (`tests/data/` holds reference results of stage 1-2) |
| `docs/grid_example.png` | Snapshot of the city map mid-simulation |
| `REPORT_OUTLINE.md` | Outline for the 5-10 page report |

## 4. Architecture and agent interaction

- **Space:** a Mesa `MultiGrid` (`width` x `height`, 20x20 by default, not
  toroidal). Each cell is a district, and several agents can share a cell.
- **Agents:** `TaxiAgent` and `PassengerAgent` are subclasses of `mesa.Agent`.
- **Scheduling:** each step uses Mesa's `AgentSet.do()` on
  `model.agents_by_type[...]`, in fixed phases. One step is one simulated minute.

Step phases:

0. Passengers whose request minute has come are created on their origin cell.
1. Each waiting passenger sends **REQUEST** (a call for proposals) to every taxi.
2. Each taxi answers with **PROPOSE**. The proposal holds `can_accept`, `eta`
   (estimated minutes until pickup) and `pickup_district` for the best feasible
   plan. With walking on, the taxi runs its plan search for the origin and for
   each neighbouring district (see section 5) and proposes the best option.
3. The passenger sends **ACCEPT** to the taxi with the lowest `eta`. Ties go to
   the lowest taxi id. With patience enabled, the passenger first ignores every
   proposal whose pickup would come after its patience runs out, keeping only
   those with `minute + eta <= request_time + patience`. If none is left, it
   sends no ACCEPT and keeps waiting.
4. The taxi re-checks the plan, because it may have accepted another passenger
   in this minute. It then either:
   - sends **CONFIRM**, which carries the promised pickup minute and the
     pickup district, and adopts the new stop list; or
   - sends **REJECT**. A rejected passenger asks again in the next minute.
5. Passengers read the replies (CONFIRM makes them *assigned*). An assigned
   passenger whose pickup district is a neighbouring district then walks
   towards it (one district per `walk_minutes_per_district`) and waits there.
6. Each taxi spends the minute either driving one cell towards its next stop,
   or standing still while a passenger boards or alights (`boarding_minutes`
   per stop). Passengers on board move with their taxi.
7. The clock advances. If patience is enabled, every passenger who is still
   *waiting* (no CONFIRM yet) and has waited `patience` minutes becomes
   **abandoned** and leaves the grid. Assigned passengers never abandon.
   When `minute == duration`, every passenger who is still waiting, assigned,
   or travelling becomes **not_completed**, and the model stops.

**Patience (optional).** Parameters `patience_min` and `patience_max`
(minutes). Each passenger draws an integer patience uniformly in
`[patience_min, patience_max]`. The draw uses its own random generator, seeded
by the seed, in request-list order. Origins, destinations and request minutes
are therefore the same with or without patience, and passenger *i* gets the
same patience in every configuration. `patience_max = None` (the default) or
`0` disables abandonment, and the model then behaves exactly as without this
feature. In the UI, set *Patience max* above 0 to enable it. In
`experiments.csv`, add optional `patience_min` / `patience_max` columns (an
empty `patience_max` cell disables it for that row).

Messages are delivered by `TaxiModel.send()`, which appends the message to the
receiver's inbox. Mesa itself has no messaging; nothing else is added on top of
Mesa's agents and scheduling.

**Taxi state:**

- position;
- capacity;
- passengers on board;
- ordered stop list of (pickup/dropoff, passenger);
- remaining boarding/alighting minutes at the current stop;
- pickup times promised to assigned passengers;
- state: idle, to_pickup, travelling, picking_up, or dropping_off;
- districts driven: total, empty, and occupied;
- busy minutes and occupied minutes.

**Passenger state:**

- origin, destination, and pickup district (the origin unless they walk);
- request minute, promised pickup minute, actual pickup minute, arrival
  minute, and abandon minute;
- patience (None when disabled);
- status: waiting, assigned, travelling, completed, not_completed, or
  abandoned;
- individual trip time;
- whether the ride was shared;
- districts ridden.

## 5. Movement and sharing rules

**Movement.** Taxis follow the shortest grid path ("x first, then y"). Entering
a cell takes `MINUTES_PER_DISTRICT` x that cell's congestion factor minutes,
so taxis never teleport. All costs are whole minutes, because one step is one
minute.

**Traffic congestion (parameter `congestion`, default `"off"`).**

| Value | Congestion factor per district |
|---|---|
| `off` | 1 everywhere |
| `center` | 3 in the central 6x6 districts (x, y in 7-12 on the 20x20 grid), 2 in the ring of districts around them (6-13), 1 elsewhere |

The UI has a *Traffic congestion* select and shades the two zones on the map.
`experiments.csv` may contain an optional `congestion` column; without it every
run uses `"off"`. With `"off"` every result is identical to the model without
congestion. On other grid sizes the 6x6 centre starts at
`((width - 6) // 2, (height - 6) // 2)`; from 10x10 up (the UI minimum) the
centre and its whole ring always fit inside the grid. On odd sizes the centre
is one district off the exact middle.

**Walking to a neighbouring district (parameters `walk_radius`, default 0 =
off, and `walk_minutes_per_district`, default 3).**

- With `walk_radius = 1`, a taxi considers as pickup district the passenger's
  origin and each adjacent district inside the grid (Manhattan distance 1),
  except the destination. It runs its normal plan search (any sharing mode)
  for each one.
- A walking pickup is allowed only if the passenger can get there first:
  `current minute + walking time <= the taxi's estimated arrival there`. The
  passenger only starts walking after the CONFIRM, which is sent in the same
  minute, so taxis never wait for walkers. (On a passenger's first request,
  the current minute is the request minute.)
- The taxi proposes its best option: earliest pickup, then earliest finish,
  then no walking (the origin wins ties).
- After the CONFIRM the passenger walks one district per
  `walk_minutes_per_district` minutes, then waits. Walking is not slowed by
  congestion. Drop-off is always at the destination.
- With `walk_radius = 0` every result is identical to the model without
  walking.

**Boarding time (delay when reaching a passenger).** At every pickup and every
drop-off, the taxi stays `boarding_minutes` in the district (default
`BOARDING_MINUTES = 1`) before driving on. Several stops in the same district
each cost `boarding_minutes`. With 0, stops are instantaneous, which
reproduces the behaviour of stages 1-2 before boarding time was added.

**Estimates vs actual movement.**

- Route **planning** uses *estimates*: the sum of the cell costs along the
  same x-first path the taxi will drive, plus `boarding_minutes` per stop,
  starting from the taxi's cell once its current stop is finished. Minutes
  the taxi has already driven towards its next cell are credited on that
  cell (it still needs at least one more minute to enter it).
- **Actual** times are measured from the simulated movement.
- The two are always equal: planning uses exactly the costs and rules of the
  movement, with or without congestion.

**Sharing modes** (parameter `sharing_mode`):

| Mode | Stage | Rule |
|---|---|---|
| `none` | 1 | Only idle taxis accept a request; one passenger at a time. |
| `no_detour` | 2 | An idle taxi accepts as in `none`. A busy taxi also accepts when the new passenger's pickup district (the origin, or with walking a neighbouring district) and destination both lie, in that order, on the cells of its current planned route. The route itself does not change. |
| `detour` | 3-4 | General **insertion search**, described below. Route changes, several stops, and up to `capacity` (1-4) passengers on board. |

**Insertion search (`detour`).**

- For a new passenger, the taxi tries every pair of positions (i, j), with
  i <= j. It inserts the pickup at position i and the drop-off at position j
  of its current stop list. Existing stops keep their order.
- This works in any state: idle, driving to a pickup, or carrying passengers.
  It also allows booking the next passenger after the current ones are
  dropped off.
- With n planned stops there are (n+1)(n+2)/2 candidate plans, each checked in
  O(n).
- A taxi takes on at most `BOOKINGS_PER_SEAT x capacity` passengers at a time
  (on board + assigned; `BOOKINGS_PER_SEAT = 2`). This keeps n at most 14 for
  capacity 4, so brute force stays cheap. Without that limit, one taxi could
  queue every passenger and the search would explode.

**Acceptance conditions.** A candidate plan, in every mode, is accepted only
if all of these hold:

- the capacity is never exceeded along the plan;
- every drop-off comes after the matching pickup;
- for **every** passenger on board or planned:
  `extra_delay = estimated in-vehicle time - individual time <= MAX_EXTRA_DELAY_MINUTES`;
- **promise rule:** for every passenger who is assigned but not yet picked up,
  the new estimated pickup is at most `MAX_EXTRA_DELAY_MINUTES` later than the
  pickup minute promised in that passenger's CONFIRM. The limit counts from
  the original promise, so several insertions together can never push a
  pickup more than 10 minutes late.

For a passenger already on board, the estimated in-vehicle time includes the
minutes already ridden. If several plans are feasible, the taxi picks the one
with the earliest pickup for the new passenger, then the earliest finish. If no
plan is feasible, the request is refused and the existing route is kept.

`MAX_EXTRA_DELAY_MINUTES = 10` stays the same in every experiment.

**Individual journey time baseline:**
`2 x boarding_minutes + travel time of the direct x-first path` (sum of its
cell costs, so congestion included). That is the time to board, drive the
shortest path alone, and alight, with no waiting and no detour. A passenger
travelling alone on a direct route therefore has an extra delay of exactly 0.
Under congestion, a shared ride can follow a different path between the same
two districts; if that path avoids slow cells, the extra delay can be
negative. For a passenger who walked, the baseline starts at the pickup
district: the walk is the passenger's choice, not a delay caused by sharing.

## 6. Metrics

All times are in simulated minutes.

**When times are recorded:**

- `pickup_time` is the minute the taxi reaches the pickup district (the
  origin, or the district the passenger walked to), when boarding starts.
- `arrival_time` is the minute alighting at the destination ends.

| Metric | Definition |
|---|---|
| Waiting time | pickup - request. For a passenger who walked, this includes the walk. Patience is compared with this same pickup time. |
| In-vehicle time | arrival - pickup. Includes own boarding/alighting, detours, and other passengers' stops. |
| Total journey time | arrival - request (waiting + in-vehicle) |
| Extra delay | in-vehicle time - individual time (both from the pickup district). 0 for a solo direct trip; above 0 only because of sharing. |

Averages marked "completed" include only passengers who reached their
destination. The completed count is always reported next to them, because
unfinished trips are excluded.

Other reported values:

- **Average extra delay:** reported over all completed passengers, and also
  over completed passengers who shared a ride.
- **Average waiting time including unserved:** every created passenger counts.
  Unserved passengers count the minutes they had waited at the deadline, so
  this value is a lower bound. Abandoned passengers count the minutes until
  they gave up.
- **Abandoned:** `abandoned` passengers gave up waiting for a CONFIRM after
  their patience; `abandoned_pct` is their share of created passengers. They
  are not counted in `not_completed`. Both are 0 when patience is disabled.
- **Acceptable trips:** `acceptable_pct` is the percentage of created
  passengers who completed with `waiting time <= patience` and
  `extra delay <= MAX_EXTRA_DELAY_MINUTES`. With patience disabled, any
  completion meets the waiting condition. A passenger can complete without
  being acceptable: an assigned passenger never abandons, but may still be
  picked up after their patience has run out.
- **Walking:** `walked_pct` is the share of completed passengers who were
  picked up in a neighbouring district. `avg_walk_minutes` is the mean walking
  time over completed passengers (0 for those who did not walk). Both are 0
  when walking is off. `passengers.csv` also records each passenger's
  `pickup_district` and `walk_minutes`.
- **Taxi distance (vehicle-km proxy):** districts driven, split into
  `empty_distance` (no passenger on board) and `occupied_distance`.
  `total_distance` is their sum. `empty_distance_pct` is the empty share.
  Distance per completed passenger is also reported.
- **Passenger distance (passenger-km proxy):** `passenger_distance` sums the
  districts each passenger rode.
- **Average occupancy:** `avg_occupancy = passenger_distance / total_distance`,
  the average number of passengers per driven district.
- Comparing vehicle and passenger distance shows how much driving sharing
  saves per passenger served. These are simple proxies for vehicle travel, not
  measured pollution or congestion.
- **Utilization:** share of taxi-minutes with at least one passenger on board.
  `busy_pct` is the share of taxi-minutes with any planned stop.

## 7. Experiments

`experiments.csv` defines 10 configurations. They vary:

- capacity and sharing mode;
- arrival mode;
- fleet size (5 vs 10 taxis);
- demand (40/60/100 passengers);
- duration (60 or 120 minutes).

Fixed in all configurations: 20x20 grid, 1 minute per district, and
`MAX_EXTRA_DELAY_MINUTES = 10`. Every configuration runs with seeds 1-5.

Demand and taxi start cells come from separate random generators seeded only by
the seed. Configurations therefore differ only in the parameters that change:

- With the same seed, every configuration gets the same passengers: same
  origins, destinations and order.
- With 40 or 60 passengers, the passengers are the first 40/60 of the
  100-passenger list.
- With 5 taxis, the taxis are the first 5 of the 10-taxi fleet.
- Under `gradual`, request minutes are drawn uniformly in
  `[0, arrival_window)`. Under `all_at_start`, every request is at minute 0.

C1-C3 last 60 minutes; C4-C10 last 120 minutes with a 90-minute arrival window,
which leaves 30 minutes for late requests. Compare configurations of the same
duration.

## 8. Assumptions and limitations

- The grid is abstract: no road network and no traffic from other vehicles.
  All taxis have the same speed.
- Congestion is a fixed, optional pattern of integer slowdown factors (centre
  x3, ring x2). It does not change over time and does not depend on how many
  taxis are in a district. Routes do **not** avoid congestion: taxis keep the
  x-first path even when a detour around the centre would be faster.
- Every pickup and drop-off takes the same fixed time (`boarding_minutes`).
- Taxi assignment is a one-round, greedy auction run each minute. A passenger
  accepts the lowest estimated pickup time. If that taxi has just been taken by
  someone else, the passenger retries one minute later. There is no global
  optimization and no reassignment once a taxi is confirmed.
- Insertion only places the new passenger's two stops; existing stops are
  never reordered.
- The booking limit (`BOOKINGS_PER_SEAT = 2`) is a practical bound, not a
  modelling result. It keeps about 95 % of the unbounded throughput in a test
  configuration (48 % vs 51 % completed), while keeping each step fast.
- With `boarding_minutes` > 0, a third or fourth passenger is rarely accepted.
  Every extra stop costs the others time, so the 10-minute limit is reached
  quickly.
- Patience is a simple acceptability rule: a fixed integer per passenger,
  drawn uniformly, compared only with the time spent waiting for a CONFIRM.
  Once confirmed, a passenger trusts the promise and never abandons, however
  late the pickup. An abandoned passenger does not request again. The
  experiments in `results/` were run with patience disabled.
- A passenger only accepts a pickup promised within its patience, but a
  confirmed pickup can still slip up to `MAX_EXTRA_DELAY_MINUTES` past the
  promise when the taxi later takes on other passengers. A few accepted trips
  may therefore still wait longer than their patience; they complete, but do
  not count in `acceptable_pct`.
- Walking is limited to one adjacent district, decided by the taxi's offer,
  and only at the pickup (never at the destination). The passenger does not
  compare walking against waiting for a better offer, and walking time is not
  counted as a cost in the extra-delay limit. Walking speed is fixed and
  unaffected by congestion. A taxi never waits for a walker, so a walking
  pickup is only offered when the taxi is at least the walking time away.
- Idle taxis wait where they are; there is no repositioning.
- Requests made at or after the deadline are not created.
- The grid size changes the generated demand and taxi start cells, so results
  on different grid sizes are not comparable passenger by passenger. The
  congestion zone keeps its 6x6 size on any grid, so it covers a smaller
  share of a larger city.
- Results depend on the chosen grid size and demand levels. Each configuration
  is averaged over only 5 seeds.
- The city map is drawn by `app.draw_city` from the model, because routes and
  planned stops are not single agents. Mesa's `make_space_component` is not
  used, so its zorder bug in 3.5.1 does not apply.
