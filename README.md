# Taxi-Sharing Multi-Agent Simulation (Mesa)

Master's project for *Foundations of Agent-Based Systems*.

**Research question:** How does taxi sharing affect the number of passengers
served, passenger waiting times, journey times, and taxi distance travelled
under different simulation configurations?

The model also has four optional features that can be switched on one by one:
**buses**, **walking** to a neighbouring district, traffic **congestion**, and
passenger **patience**. Everything else is a fixed study setting (section 4).

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

Check that the environment is really active before running anything:
`python -c "import sys; print(sys.executable)"` must print the `taxi-mesa`
Python. If `conda activate` does not work in your terminal, call that Python
by its full path (for example
`C:\Users\<you>\anaconda3\envs\taxi-mesa\python.exe -m solara run app.py`).

## 2. Running

All commands are run from the project folder.

| Task | Command |
|---|---|
| Interactive visualization | `python -m solara run app.py` then open http://localhost:8765 |
| All experiments (S1-S12 x seeds 1-10) | `python run_experiments.py` (about 1 minute) |
| Selected scenarios / seeds | `python run_experiments.py --only S4 S12 --seeds 1 2` |
| Analysis experiments (section 8) | `python run_experiments.py --config experiments_sweep.csv --out results_sweep --no-charts`, the same with `experiments_fleet.csv` / `results_fleet`, then `python plot_analysis.py` (a few minutes) |
| Tests | `python -m pytest` |

Stop the server with **Ctrl+C** in its terminal.

### Sidebar

Controls: *Reset*, *Step*, and ▶ / ❚❚ (play/pause). Model parameters:

| Control | Values |
|---|---|
| Sharing mode | `none`, `no_detour`, `detour` (section 6) |
| Taxi capacity | 1-4 seats |
| Number of taxis | 1-40 (base: 20) |
| Number of passengers | 1-200 (base: 90) |
| Seed | 1-100 |
| Buses | on/off (section 6) |
| Walking to neighbour district | on/off (section 6) |
| Traffic congestion | on/off (section 5) |
| Passenger patience | on/off: patience 10-30 min (section 4) |

Every other setting is fixed (section 4). After changing a parameter, press
*Reset* to rebuild the model. The simulation stops by itself at minute 120.
Each step redraws two images, so Play runs at about 1-2 minutes per second.

**Leave "Use Threads" off** (its default). Mesa always shows this checkbox,
but with it ticked the model steps in another thread while the map is being
drawn, so the app lags or shows half-updated frames. To go faster, raise
**Render Interval** instead (for example to 5: the map and charts are then
redrawn every 5 simulated minutes).

The page shows:

- the city map (example with all four features: `docs/grid_example.png`;
  also `docs/map_S1.png`, `docs/map_S6.png`, `docs/map_S12.png`, all at
  minute 40, seed 1);
- a status panel: minute, configuration, and a results table (with buses on,
  extra rows compare taxi and bus passengers);
- a 2x2 chart panel over time: passengers by status, average times, taxi
  distance (total / occupied / empty), and taxi utilization.

The panels can be dragged and resized.

### Map legend

A box above the map lists the active features ("Buses on · Walking off ·
..."). The legend is grouped in sections; only the active ones are shown.

| Section | Symbol | Meaning |
|---|---|---|
| Taxis | grey / orange / blue square | taxi idle / driving to a pickup / driving to a drop-off |
| | green / purple square | taxi stopped: a passenger is boarding / alighting |
| | `2/4` next to a taxi | passengers on board / seats |
| | thin line | the taxi's planned route, in the taxi's colour |
| | ▲ / ▼ | planned pickup / planned drop-off of that taxi |
| Buses | wide light band | a bus line ("road"), one colour per line (H1-H3, V1-V3) |
| | small white square | bus stop |
| | rounded box with `3/10` | bus in its line colour: passengers on board / 10 |
| Passengers | red dot | taxi passenger waiting, no taxi yet |
| | yellow dot | taxi passenger waiting, a taxi is assigned |
| | number in a dot | several passengers in that district |
| | teal diamond + dashed arrow | taxi passenger walking to a neighbouring pickup district (walking on) |
| | filled pentagon (line colour) | bus passenger waiting at a stop; number = several |
| | hollow pentagon | bus passenger walking to the stop or to the destination |
| | brown ring | passenger who abandoned, at their origin (patience on) |
| | black cross | passenger not completed at the deadline |
| Zones | darker / lighter orange | congestion centre x3 / ring x2 (congestion on) |

Bus riders are not drawn separately: they are counted in their bus's label.
Where two lines cross, two buses in the same district can partly overlap.

### Experiments

The scenarios are listed in `experiments.csv`; edit that file to define new
ones (the code does not need to change). Results are written to `results/`:

- `runs.csv`: one row per scenario and seed, with all metrics;
- `summary.csv`: mean and standard deviation over seeds per scenario;
- `passengers.csv`: every passenger in every run (mode, times, status,
  walking, extra delay);
- `charts/*.png`: comparison bar charts, one per metric, and `comparison.png`
  with all eight. Bars are coloured and hatched by sharing mode; under each
  scenario id a short tag shows the features switched on (`+bus`, `+walk`,
  `+cong`, `+pat`, `all 4`).

Columns of `experiments.csv`:

| Column | Meaning |
|---|---|
| `config_id`, `description` | name and text |
| `num_taxis`, `num_passengers`, `capacity`, `sharing_mode` | required |
| `buses`, `walking`, `congestion`, `patience` | optional `True`/`False`, mapped to model parameters exactly like the sidebar checkboxes; absent = off |
| any other model parameter | optional, for older files: `duration`, `arrival_mode`, `arrival_window`, `width`, `height`, `boarding_minutes`, `walk_radius`, `walk_minutes_per_district`, `patience_min`, `patience_max` (empty = off), `congestion` as `off`/`center`. Absent = the fixed default. |

### Troubleshooting

- **Blank main area** (only the sidebar is visible; the browser console shows
  `GlobalVue.use is not a function`): the server runs in a Python with the
  Vue 3 widget packages (`ipyvue`/`ipyvuetify` 3.x), usually the base
  Anaconda Python instead of `taxi-mesa`. Mesa 3.5.1's dashboard needs the
  Vue 2 lines pinned in `requirements.txt`. Start the server with the
  `taxi-mesa` Python (section 1).
- **DLL error:** if `solara run` fails with
  `ImportError: DLL load failed while importing _imaging` and the traceback
  shows paths of another Python installation, the `VIRTUAL_ENV` environment
  variable points to that installation and IPython adds its packages to the
  search path. Clear it (PowerShell: `Remove-Item Env:VIRTUAL_ENV`) and start
  again.
- After editing the code, restart the server: Solara's automatic reload can
  fail on this app.

## 3. Files

| File | Content |
|---|---|
| `config.py` | Fixed settings and constants (`MAX_EXTRA_DELAY_MINUTES = 10`, grid, duration, bus, walking, patience and congestion settings), base scenario `DEFAULTS`, `feature_params()` for the four features |
| `messages.py` | `Message` class and message types |
| `routing.py` | Manhattan distance, x-first grid path, congestion zones and factors |
| `agents.py` | `TaxiAgent`, `PassengerAgent` (Mesa agents): messaging, route planning, sharing rules, walking, bus journeys |
| `buses.py` | `BusLine`, `BusAgent` (Mesa agent), line layout, mode choice (`choose_bus_trip`) |
| `model.py` | `TaxiModel`: `MultiGrid`, demand generation, step phases, deadline, `DataCollector` |
| `metrics.py` | Metric definitions used by the model, the UI and the experiments |
| `app.py` | Mesa `SolaraViz` interface: sidebar (`UITaxiModel`), city map (`draw_city`), status panel, charts |
| `run_experiments.py` | Experiment runner (Mesa `batch_run`), CSV export, charts |
| `experiments.csv` | The 12 scenarios S1-S12 |
| `experiments_sweep.csv`, `experiments_fleet.csv` | Analysis experiments: load sweep and fleet sizes (section 8) |
| `plot_analysis.py` | Line charts and fleet-equivalence table for the analysis experiments |
| `results_sweep/`, `results_fleet/`, `results_analysis/` | Their results, charts and `findings.md` |
| `tests/` | Pytest suite (`tests/data/` holds reference results of stages 1-2) |
| `docs/` | Map snapshots (`grid_example.png` = `map_S12.png`, `map_S1.png`, `map_S6.png`) |
| `REPORT_OUTLINE.md` | Outline for the 5-10 page report |

## 4. Architecture and fixed settings

- **Space:** a Mesa `MultiGrid`, 30x30, not toroidal. Each cell is a
  district; several agents can share a cell.
- **Agents:** `TaxiAgent`, `PassengerAgent` and `BusAgent` are subclasses of
  `mesa.Agent`.
- **Scheduling:** each step runs fixed phases with Mesa's `AgentSet.do()` on
  `model.agents_by_type[...]`. One step is one simulated minute.

**Fixed settings** (`config.py`; the same in the UI and every experiment):

| Setting | Value |
|---|---|
| City | 30x30 districts |
| Duration | 120 minutes |
| Requests | gradual: request minutes uniform in the first 90 minutes |
| Taxi speed | 1 minute per district (times the congestion factor) |
| Boarding | 1 minute at every pickup and drop-off (taxis and buses) |
| Maximum extra delay | `MAX_EXTRA_DELAY_MINUTES = 10` |
| Patience (when on) | uniform integer in 10-30 minutes |
| Walking | 3 minutes per district |
| Buses (when on) | 6 lines, 2 buses each, 10 seats, stops every 3 districts; bus only for trips of 6+ districts with stops within 3 districts of both ends |
| Base fleet / demand | 20 taxis, 90 passengers (calibrated, section 7) |

`TaxiModel` still accepts every parameter (grid size, duration, ...) so tests
and older experiment files can set them; the UI and `experiments.csv` vary
only sharing mode, capacity, fleet, demand, seed and the four features.

**Step phases:**

0. Passengers whose request minute has come are created on their origin. Each
   chooses its mode once, here: the bus if a bus line serves both ends
   (section 6), otherwise a taxi.
1. Each waiting taxi passenger sends **REQUEST** (a call for proposals) to
   every taxi.
2. Each taxi answers with **PROPOSE**: `can_accept`, `eta` (minutes until
   pickup) and `pickup_district` of its best feasible plan. With walking on,
   the taxi searches plans for the origin and each neighbouring district.
3. The passenger sends **ACCEPT** to the taxi with the lowest `eta` (ties: the
   lowest taxi id). With patience on, it first ignores every proposal whose
   pickup would come after its patience runs out
   (`minute + eta <= request_time + patience`); if none is left it sends no
   ACCEPT and keeps waiting.
4. The taxi re-checks the plan (it may have accepted someone else this
   minute), then sends **CONFIRM** (promised pickup minute and pickup district)
   and adopts the new stop list, or **REJECT** (the passenger asks again next
   minute).
5. Passengers read the replies (CONFIRM makes them *assigned*). Then everyone
   who walks this minute does: taxi passengers to a neighbouring pickup
   district, bus passengers to their stop or from it to their destination.
6. Each taxi drives towards its next stop or stands while a passenger boards
   or alights; passengers on board move with it. Then each bus drives or
   stands at a stop.
7. The clock advances. With patience on, a taxi passenger still *waiting*
   (no CONFIRM) after `patience` minutes becomes **abandoned** and leaves the
   grid. At minute 120, everyone still waiting, assigned or travelling becomes
   **not_completed**, and the model stops.

Messages are delivered by `TaxiModel.send()`, which appends the message to the
receiver's inbox; Mesa itself has no messaging. Bus passengers never send
messages: buses follow fixed lines.

**Patience (feature).** Each taxi passenger draws an integer patience in
10-30 minutes from its own random generator (seeded by the seed, in
request-list order), so demand is identical with or without patience and
passenger *i* gets the same patience in every scenario. Assigned passengers
never abandon. Bus passengers have no patience.

**Taxi state:** position; capacity; passengers on board; ordered stop list of
(pickup/dropoff, passenger); remaining boarding/alighting minutes; pickup
times promised to assigned passengers; state (idle, to_pickup, travelling,
picking_up, dropping_off); districts driven (total, empty, occupied); busy and
occupied minutes.

**Passenger state:** origin, destination; mode (taxi/bus); pickup district
(origin unless walking); for bus passengers the line, boarding and alighting
stops and the journey stage (to stop, at stop, riding, to destination);
request, promised pickup, pickup, alighting, arrival and abandon minutes;
patience; status (waiting, assigned, travelling, completed, not_completed,
abandoned); whether the ride was shared; districts ridden in a taxi.

**Bus state:** line, position and direction on the line, passengers on board,
remaining minutes at the current stop, districts driven and passenger-districts
carried.

## 5. Movement and congestion

**Movement.** Taxis follow the shortest grid path ("x first, then y").
Entering a district takes `MINUTES_PER_DISTRICT` x that district's congestion
factor minutes, so vehicles never teleport. All costs are whole minutes.

**Traffic congestion (feature).** The central rectangle of one third of the
grid in each direction (10x10 districts, x and y in 10-19 on 30x30) has factor
3; the ring of districts around it (9-20) factor 2; all others factor 1. Taxis
and buses are slowed; walking is not. Routes do not avoid congestion.

**Boarding time.** At every pickup and drop-off a taxi stands 1 minute in the
district before driving on; several stops in one district each cost 1 minute.

**Estimates vs actual movement.** Route planning sums the district costs along
the same x-first path the taxi will drive, plus the boarding minutes, starting
when its current stop is finished; minutes already driven towards the next
district are credited. Planning therefore uses exactly the costs and rules of
the movement: estimates equal actual times.

## 6. Sharing, walking and bus rules

**Sharing modes** (`sharing_mode`):

| Mode | Stage | Rule |
|---|---|---|
| `none` | 1 | Only idle taxis accept a request; one passenger at a time. |
| `no_detour` | 2 | An idle taxi accepts as in `none`. A busy taxi also accepts when the new passenger's pickup district and destination both lie, in that order, on the cells of its current planned route. The route does not change. |
| `detour` | 3-4 | General **insertion search**: route changes, several stops, up to `capacity` (1-4) passengers on board. |

**Insertion search (`detour`).** For a new passenger the taxi tries every pair
of positions (i, j), i <= j: pickup at position i and drop-off at position j
of its stop list; existing stops keep their order. This works in any state
(idle, driving to a pickup, carrying passengers). With n planned stops there
are (n+1)(n+2)/2 plans, each checked in O(n). A taxi takes on at most
`BOOKINGS_PER_SEAT x capacity` passengers at a time (on board + assigned;
`BOOKINGS_PER_SEAT = 2`), which keeps n <= 14 and the search cheap.

**Acceptance conditions** (every mode). A plan is accepted only if:

- the capacity is never exceeded;
- every drop-off comes after its pickup;
- for every passenger on board or planned, `extra_delay = estimated in-vehicle
  time - individual time <= MAX_EXTRA_DELAY_MINUTES` (10);
- **promise rule:** no assigned passenger's pickup moves more than 10 minutes
  past the pickup minute promised in its CONFIRM (counted from the original
  promise, so several insertions together can never exceed it).

Among feasible plans the taxi picks the earliest pickup for the new passenger,
then the earliest finish. **Individual time** (the baseline for extra delay) =
2 x boarding + travel time of the direct x-first path from the pickup district,
so a solo direct trip has extra delay 0. Under congestion a shared ride can use
a different, cheaper path, so extra delay can be negative.

**Walking to a neighbouring district (feature).** A taxi also considers each
adjacent district (Manhattan distance 1, inside the grid, not the destination)
as pickup district and runs its plan search for each. A walking pickup is
offered only if the passenger can get there first: `current minute + 3 <=
the taxi's estimated arrival there` (walking starts at the CONFIRM, sent in
the same minute), so taxis never wait for walkers. The taxi proposes the
earliest pickup, then earliest finish, then no walking. Drop-off is always at
the destination. Waiting time includes the walk; individual time and extra
delay are measured from the pickup district.

**Buses (feature).**

- **Lines:** three horizontal lines along rows h/4, h/2 and 3h/4 (H1-H3) and
  three vertical lines along columns w/4, w/2 and 3w/4 (V1-V3): rows/columns
  7, 15 and 22 on 30x30. Stops every 3 districts along each line, including
  both ends.
- **Buses:** 2 per line (12 in all), 10 seats, spread evenly over the line at
  the start, driving back and forth at taxi speed (congestion applies). A bus
  stands 1 minute at a stop only when someone boards or alights.
- **Mode choice** (once, at creation): if the trip is at least 6 districts
  long (Manhattan distance origin to destination, `BUS_MIN_TRIP`) and one line
  has a stop within 3 districts (`BUS_WALK_MAX`) of the origin and a
  *different* stop within 3 districts of the destination, the passenger takes
  the bus, using the line and stops with the least total walking; otherwise
  it calls a taxi. No transfers between lines.
- **Bus journey:** walk to the boarding stop (3 min per district), wait,
  board the first bus that reaches the stop heading towards the alighting
  stop with a free seat, ride, alight, walk to the destination. Arrival =
  end of that walk. Bus passengers send no taxi requests and have no
  patience; at minute 120 unfinished bus passengers are not_completed.

## 7. Metrics

All times are in simulated minutes. Averages marked "completed" include only
passengers who reached their destination; the completed count or percentage
is always reported next to them.

| Metric | Definition |
|---|---|
| Waiting time | pickup - request. Pickup = the taxi reaches the pickup district, or the passenger boards the bus. Includes walking to the pickup district or bus stop. Patience is compared with this pickup time. |
| In-vehicle time | pickup to end of alighting |
| Total journey time | arrival - request. For bus passengers arrival = end of the walk to the destination. |
| Extra delay | taxi passengers only: in-vehicle time - individual time. 0 for a solo direct trip; above 0 only because of sharing. |

| Reported value | Meaning |
|---|---|
| `completed_pct`, `avg_wait_completed`, `avg_total_completed` | over all passengers (taxi and bus) |
| `..._taxi`, `..._bus` | the same three split by mode (empty when a mode has no passengers) |
| `avg_extra_delay_completed`, `max_extra_delay`, `avg_extra_delay_shared` | taxi passengers only (buses have no direct-ride baseline) |
| `avg_wait_censored` | every created passenger; unserved ones count their wait up to the deadline (a lower bound), abandoned ones up to giving up |
| `abandoned`, `abandoned_pct` | taxi passengers who gave up waiting for a CONFIRM (not counted in `not_completed`) |
| `acceptable_pct` | % of created passengers who completed with waiting time <= patience (always true without patience, and for bus passengers) and extra delay <= 10 min (taxi passengers) |
| `walked_pct`, `avg_walk_minutes` | % of completed passengers who walked at all (to a neighbouring pickup district, or to/from a bus stop), and mean walking minutes over completed passengers (0 for those who did not walk) |
| `bus_share_pct` | % of created passengers who took the bus |
| `total_distance`, `empty_distance`, `occupied_distance`, `empty_distance_pct` | taxi districts driven (vehicle-km proxy), split by whether anyone was on board |
| `distance_per_completed` | taxi distance per completed passenger (taxi and bus passengers) |
| `passenger_distance`, `avg_occupancy` | districts ridden in taxis; `avg_occupancy` = passenger distance / taxi distance |
| `bus_distance`, `avg_bus_occupancy` | districts driven by buses; bus passenger-districts / bus distance |
| `utilization_pct`, `busy_pct` | share of taxi-minutes with a passenger on board / with any planned stop |

The distances are simple proxies for vehicle travel, not measured pollution or
congestion.

## 8. Experiments

**Calibration.** The base scenario was chosen so that sharing `none` with
capacity 1 serves roughly 50-70 % of passengers. Tried on the fixed settings,
seeds 1-5 (S1 completed % / detour capacity 4 completed %):

| Taxis | 60 passengers | 80 | 90 | 100 | 120 | 150 |
|---|---|---|---|---|---|---|
| 10 | 43.7 / 65.0 | | | 26.0 / 46.0 | | 16.5 / 31.9 |
| 15 | 60.3 / 86.3 | | | 39.6 / 65.8 | | 27.2 / 47.7 |
| 20 | 79.0 / 91.3 | 64.8 / 89.0 | **57.6 / 86.7** | 51.8 / 81.6 | | 36.5 / 62.3 |
| 25 | | | | 65.4 / 89.8 | 54.7 / 85.5 | |

Chosen: **20 taxis, 90 passengers** (S1: 58.3 % over seeds 1-10, every seed
in range), which leaves room both above (sharing) and below (congestion).

**Scenarios** (`experiments.csv`, seeds 1-10, all with 20 taxis and 90
passengers):

| Id | Sharing | Capacity | Features |
|---|---|---|---|
| S1 | none | 1 | – |
| S2 | no_detour | 2 | – |
| S3 | detour | 2 | – |
| S4 | detour | 4 | – |
| S5 | detour | 4 | walking |
| S6 | detour | 4 | buses |
| S7 | none | 1 | buses |
| S8 | detour | 4 | congestion |
| S9 | none | 1 | congestion |
| S10 | detour | 4 | patience |
| S11 | none | 1 | patience |
| S12 | detour | 4 | all four |

S1-S4 isolate the sharing level; S5-S11 add one feature to the best sharing
setup (S4) and, for buses, congestion and patience, also to no sharing (S1);
S12 combines everything. Demand and taxi start cells come from separate
random generators seeded only by the seed, so for a given seed every scenario
gets exactly the same passengers (origins, destinations, request minutes) and
taxi starts.

**Results** (mean ± standard deviation over seeds 1-10; `results/summary.csv`,
charts in `results/charts/`):

| Id | Features | Completed % | Wait (min) | Total (min) | Extra delay (min) | Taxi dist./completed | Empty % | Bus % | Acceptable % |
|---|---|---|---|---|---|---|---|---|---|
| S1 | – | 58.3 ± 3.3 | 21.6 ± 3.3 | 42.5 ± 3.7 | 0.0 ± 0.0 | 39.5 ± 2.1 | 45.3 ± 2.6 | 0.0 | 58.3 ± 3.3 |
| S2 | – | 58.1 ± 2.9 | 21.2 ± 3.1 | 42.1 ± 3.4 | 0.0 ± 0.0 | 39.6 ± 2.0 | 45.7 ± 2.9 | 0.0 | 58.1 ± 2.9 |
| S3 | – | 84.0 ± 3.1 | 10.6 ± 1.7 | 35.2 ± 2.6 | 3.6 ± 0.4 | 24.1 ± 1.2 | 20.8 ± 1.9 | 0.0 | 84.0 ± 3.1 |
| S4 | – | 86.3 ± 2.7 | 10.0 ± 1.4 | 34.8 ± 2.3 | 3.9 ± 0.2 | 23.0 ± 0.8 | 20.5 ± 1.2 | 0.0 | 86.3 ± 2.7 |
| S5 | walk | 88.7 ± 4.9 | 8.7 ± 1.1 | 33.6 ± 2.0 | 4.0 ± 0.3 | 21.9 ± 1.1 | 17.6 ± 1.9 | 0.0 | 88.7 ± 4.9 |
| S6 | bus | 88.1 ± 2.9 | 10.4 ± 1.3 | 35.1 ± 2.0 | 3.4 ± 0.4 | 20.6 ± 1.3 | 20.3 ± 2.3 | 15.8 ± 3.7 | 88.1 ± 2.9 |
| S7 | bus | 67.7 ± 5.0 | 18.6 ± 2.9 | 40.5 ± 3.4 | 0.0 ± 0.0 | 33.4 ± 2.9 | 44.8 ± 2.2 | 15.8 ± 3.7 | 67.7 ± 5.0 |
| S8 | cong | 69.4 ± 5.0 | 12.4 ± 1.4 | 42.6 ± 2.5 | 2.8 ± 0.6 | 25.7 ± 1.9 | 21.9 ± 2.7 | 0.0 | 69.4 ± 5.0 |
| S9 | cong | 40.8 ± 2.4 | 22.4 ± 2.9 | 49.6 ± 4.1 | 0.0 ± 0.0 | 42.3 ± 3.2 | 47.8 ± 2.2 | 0.0 | 40.8 ± 2.4 |
| S10 | pat | 81.0 ± 3.9 | 8.1 ± 0.8 | 33.2 ± 1.5 | 3.8 ± 0.3 | 22.9 ± 1.3 | 18.4 ± 1.3 | 0.0 | 78.1 ± 3.1 |
| S11 | pat | 66.8 ± 3.8 | 12.6 ± 1.0 | 33.6 ± 1.9 | 0.0 ± 0.0 | 31.0 ± 1.9 | 31.8 ± 2.5 | 0.0 | 66.8 ± 3.8 |
| S12 | all 4 | 75.8 ± 5.4 | 10.0 ± 1.2 | 40.3 ± 1.5 | 2.8 ± 0.4 | 19.9 ± 1.7 | 17.0 ± 2.3 | 15.8 ± 3.7 | 73.8 ± 5.1 |

Abandoned with patience: S10 10.8 ± 4.4 %, S11 26.7 ± 3.2 %, S12 8.0 ± 3.2 %.

By mode, in the bus scenarios (completed % / wait / total time, minutes):

| Id | Taxi passengers | Bus passengers | Bus occupancy |
|---|---|---|---|
| S6 | 88.6 ± 3.7 / 8.8 ± 1.5 / 34.1 ± 2.4 | 86.0 ± 9.7 / 19.0 ± 2.6 / 39.8 ± 2.8 | 0.13 ± 0.03 |
| S7 | 64.4 ± 5.2 / 18.4 ± 3.5 / 40.6 ± 4.0 | 86.0 ± 9.7 / 19.0 ± 2.6 / 39.8 ± 2.8 | 0.13 ± 0.03 |
| S12 | 75.3 ± 6.7 / 7.7 ± 0.8 / 39.0 ± 1.4 | 78.2 ± 14.5 / 21.8 ± 4.1 / 47.2 ± 6.6 | 0.14 ± 0.04 |

Bus passengers' waiting time includes the walk to the stop; their total time
includes both walks.

**Driving with buses.** The "Taxi dist./completed" column counts taxis only.
Buses also drive: their full lines, whatever their load. Counting both
(vehicle distance = taxi + bus, per run, in districts):

| Id | Taxi distance | Bus distance | Vehicle distance | Vehicle dist./completed |
|---|---|---|---|---|
| S1 (no buses) | 2066.9 ± 51.1 | 0 | 2066.9 ± 51.1 | 39.5 ± 2.1 |
| S4 (no buses) | 1783.7 ± 81.8 | 0 | 1783.7 ± 81.8 | 23.0 ± 0.8 |
| S6 | 1634.9 ± 103.7 | 1413.6 ± 5.5 | 3048.5 ± 106.8 | 38.5 ± 1.6 |
| S7 | 2023.4 ± 76.9 | 1413.6 ± 5.5 | 3437.0 ± 77.7 | 56.8 ± 4.6 |
| S12 | 1350.9 ± 87.6 | 1217.9 ± 4.6 | 2568.8 ± 89.8 | 37.8 ± 2.8 |

So the buses lower the *taxi* distance but raise the *total* vehicle distance
at this demand: they carry only about 0.13 passengers per district driven. (In
S12 congestion slows the buses, so they cover fewer districts.) A bus is a
bigger vehicle than a taxi, so bus districts are not directly comparable to
car districts for pollution or road space; the totals count vehicle movements
only.

These numbers are copied from the run of the current code; re-run
`python run_experiments.py` after any change and update the table from
`results/summary.csv`.

**Analysis experiments.** Two extra sets on the same fixed settings, seeds
1-10, run with the commands in section 2 (they do not touch `results/`):

- **Load sweep** (`experiments_sweep.csv` → `results_sweep/`): 20 taxis, 30,
  60, 90, 120, 150 and 180 passengers, for single rides (none, capacity 1) and
  detour sharing with capacity 2 and 4.
- **Fleet equivalence** (`experiments_fleet.csv` → `results_fleet/`): 90
  passengers; single rides with 10-30 taxis, detour sharing (capacity 4) with
  6-24 taxis, and the same plus buses with 6-24 taxis (steps of 2).

`plot_analysis.py` draws `results_analysis/sweep.png` and `fleet.png` (mean
line, ± 1 std band, one line per mode) and writes
`results_analysis/fleet_equivalence.csv`: per mode, the smallest fleet whose
mean completed % reaches the S1 level (58.3 %) and 85 %, with taxi distance,
bus distance and their sum (vehicle distance, per run). In `fleet.png` the
dashed line is the taxi + bus distance of the bus mode.

| Mode | Target | Taxis | Completed % | Taxi distance | Bus distance | Vehicle distance | Empty taxi % |
|---|---|---|---|---|---|---|---|
| none, cap 1 | S1 level | 20 | 58.3 ± 3.3 | 2066.9 ± 51.1 | 0 | 2066.9 ± 51.1 | 45.3 ± 2.6 |
| detour, cap 4 | S1 level | 12 | 59.8 ± 4.2 | 1219.1 ± 23.9 | 0 | 1219.1 ± 23.9 | 24.0 ± 3.3 |
| detour, cap 4 + buses | S1 level | 10 | 58.7 ± 3.6 | 1023.2 ± 26.3 | 1413.6 ± 5.5 | 2436.8 ± 27.7 | 25.4 ± 3.5 |
| none, cap 1 | 85 % | not reached (81.9 ± 5.4 % with 30 taxis, 2666.8 ± 143.6 districts) | | | | | |
| detour, cap 4 | 85 % | 20 | 86.3 ± 2.7 | 1783.7 ± 81.8 | 0 | 1783.7 ± 81.8 | 20.5 ± 1.2 |
| detour, cap 4 + buses | 85 % | 18 | 85.3 ± 3.3 | 1604.0 ± 82.3 | 1413.6 ± 5.5 | 3017.6 ± 84.4 | 22.0 ± 3.0 |

Detour sharing without buses gives the same service as single rides with 8
fewer taxis and 41.0 % less driving (1219.1 vs 2066.9 districts). Adding buses
saves 2 more taxis and some taxi driving, but the buses' own 1413.6 districts
make the total vehicle distance higher than single rides at this demand (2436.8
vs 2066.9 districts, +18 %), because the buses drive their full lines while
carrying about 0.13 passengers per district. Bus districts are not directly
comparable to car districts (bigger vehicle).

`results_analysis/findings.md` summarises what both sets and S1-S12 show
(when sharing helps, taxis and driving saved, the waiting / in-vehicle
trade-off, and the effect of each feature).

## 9. Assumptions and limitations

- The grid is abstract: no road network, no traffic from other vehicles. All
  taxis and buses have the same speed.
- Congestion is a fixed pattern of integer slowdown factors (centre x3, ring
  x2). It does not change over time or with the number of vehicles. Routes
  do **not** avoid congestion: vehicles keep the x-first path even when a
  detour around the centre would be faster.
- Every pickup and drop-off takes the same fixed time (1 minute).
- Taxi assignment is a one-round greedy auction each minute: the passenger
  accepts the lowest estimated pickup; if that taxi was just taken, it retries
  next minute. No global optimisation, no reassignment after CONFIRM.
- Insertion only places the new passenger's two stops; existing stops are
  never reordered.
- The booking limit (`BOOKINGS_PER_SEAT = 2`) is a practical bound, not a
  modelling result.
- With 1-minute stops, a third or fourth passenger is rarely accepted: every
  extra stop costs the others time, so the 10-minute limit is reached quickly
  (S4 is close to S3).
- **Patience** is a simple rule: a fixed integer per passenger, compared only
  with the time spent waiting for a CONFIRM. A passenger accepts only a pickup
  promised within its patience, but a confirmed pickup can still slip up to
  10 minutes past the promise when the taxi later takes on others; such trips
  complete but do not count as acceptable. An abandoned passenger does not
  request again. Abandoning frees taxis for others, so completion can rise
  with patience (S11 vs S1).
- **Walking** is limited to one adjacent district at the pickup, decided by
  the taxi's offer; the passenger does not compare walking with waiting for
  a better offer, and walking time is not limited by the extra-delay rule.
- **Buses:** fixed lines and timetable-free back-and-forth service; **no
  transfers** between lines; the **mode choice rule** is a fixed walking
  threshold (trip of at least 6 districts, both ends within 3 districts of
  stops on one line), decided once and never revised (a bus passenger never
  switches to a taxi, even when a taxi would be faster). On 30x30 about 16 %
  of passengers take the bus. Buses always drive their full lines, so bus
  occupancy stays low (about 0.13-0.14 passengers per bus-district).
- **Buses add driving:** with buses on, the total vehicle distance (taxi + bus)
  is higher than with single rides at this demand, although the taxi distance
  is lower (section 8).
- **Bus-km are not car-km:** `bus_distance` is reported separately from taxi
  distance. A bus district and a taxi district differ in emissions and road
  space, so the two cannot be added or compared directly as a pollution or
  congestion measure.
- Idle taxis wait where they are; there is no repositioning.
- Requests at or after the deadline are not created.
- Results depend on the chosen city size, fleet and demand; each scenario is
  averaged over 10 seeds.
- The city map is drawn by `app.draw_city` from the model (routes, stops and
  bus lines are not single agents). Mesa's `make_space_component` is not used,
  so its zorder bug in 3.5.1 does not apply.
