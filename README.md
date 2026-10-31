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

- number of taxis and number of passengers;
- capacity (1-4) and sharing mode;
- boarding time per stop;
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

**Experiments.** The configurations are listed in `experiments.csv`. Edit that
file to define new scenarios; the source code does not need to change. Results
are written to `results/`:

- `runs.csv`: one row per configuration and seed, with all metrics.
- `summary.csv`: mean and standard deviation over seeds for each configuration.
- `passengers.csv`: every passenger in every run, with times, status, and
  extra delay.
- `charts/*.png`: comparison bar charts. `comparison.png` shows all of them
  together.

`experiments.csv` may contain an optional `boarding_minutes` column. Without it,
every run uses `BOARDING_MINUTES` from `config.py`.

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
| `routing.py` | Manhattan distance, grid path, travel-time estimate |
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

- **Space:** a Mesa `MultiGrid` (20x20 by default, not toroidal). Each cell is a
  district, and several agents can share a cell.
- **Agents:** `TaxiAgent` and `PassengerAgent` are subclasses of `mesa.Agent`.
- **Scheduling:** each step uses Mesa's `AgentSet.do()` on
  `model.agents_by_type[...]`, in fixed phases. One step is one simulated minute.

Step phases:

0. Passengers whose request minute has come are created on their origin cell.
1. Each waiting passenger sends **REQUEST** (a call for proposals) to every taxi.
2. Each taxi answers with **PROPOSE**. The proposal holds `can_accept` and `eta`
   (estimated minutes until pickup) for the best feasible plan.
3. The passenger sends **ACCEPT** to the taxi with the lowest `eta`. Ties go to
   the lowest taxi id.
4. The taxi re-checks the plan, because it may have accepted another passenger
   in this minute. It then either:
   - sends **CONFIRM**, which carries the promised pickup minute, and adopts
     the new stop list; or
   - sends **REJECT**. A rejected passenger asks again in the next minute.
5. Passengers read the replies (CONFIRM makes them *assigned*).
6. Each taxi spends the minute either driving one cell towards its next stop,
   or standing still while a passenger boards or alights (`boarding_minutes`
   per stop). Passengers on board move with their taxi.
7. The clock advances. When `minute == duration`, every passenger who is still
   waiting, assigned, or travelling becomes **not_completed**, and the model
   stops.

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

- origin and destination;
- request minute, promised pickup minute, actual pickup minute, and arrival
  minute;
- status: waiting, assigned, travelling, completed, or not_completed;
- individual trip time;
- whether the ride was shared;
- districts ridden.

## 5. Movement and sharing rules

**Movement.** Taxis follow the shortest grid path ("x first, then y"). Each cell
takes `MINUTES_PER_DISTRICT` minutes, so taxis never teleport.

**Boarding time (delay when reaching a passenger).** At every pickup and every
drop-off, the taxi stays `boarding_minutes` in the district (default
`BOARDING_MINUTES = 1`) before driving on. Several stops in the same district
each cost `boarding_minutes`. With 0, stops are instantaneous, which
reproduces the behaviour of stages 1-2 before boarding time was added.

**Estimates vs actual movement.**

- Route **planning** uses *estimates*: Manhattan distance x minutes per
  district, plus `boarding_minutes` per stop, starting from the taxi's cell
  once its current stop is finished.
- **Actual** times are measured from the simulated movement.
- With 1 minute per district the two are equal. With slower speeds, the
  estimate ignores time already spent towards the next cell.

**Sharing modes** (parameter `sharing_mode`):

| Mode | Stage | Rule |
|---|---|---|
| `none` | 1 | Only idle taxis accept a request; one passenger at a time. |
| `no_detour` | 2 | An idle taxi accepts as in `none`. A busy taxi also accepts when the new passenger's origin and destination both lie, in that order, on the cells of its current planned route. The route itself does not change. |
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
`2 x boarding_minutes + direct Manhattan distance x minutes per district`.
That is the time to board, drive the shortest path alone, and alight, with no
waiting and no detour. A passenger travelling alone on a direct route
therefore has an extra delay of exactly 0.

## 6. Metrics

All times are in simulated minutes.

**When times are recorded:**

- `pickup_time` is the minute the taxi reaches the origin, when boarding
  starts.
- `arrival_time` is the minute alighting at the destination ends.

| Metric | Definition |
|---|---|
| Waiting time | pickup - request |
| In-vehicle time | arrival - pickup. Includes own boarding/alighting, detours, and other passengers' stops. |
| Total journey time | arrival - request (waiting + in-vehicle) |
| Extra delay | in-vehicle time - individual time. 0 for a solo direct trip; above 0 only because of sharing. |

Averages marked "completed" include only passengers who reached their
destination. The completed count is always reported next to them, because
unfinished trips are excluded.

Other reported values:

- **Average extra delay:** reported over all completed passengers, and also
  over completed passengers who shared a ride.
- **Average waiting time including unserved:** every created passenger counts.
  Unserved passengers count the minutes they had waited at the deadline, so
  this value is a lower bound.
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

- The grid is abstract: no road network, no traffic, no congestion. All taxis
  have the same speed.
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
- Idle taxis wait where they are; there is no repositioning.
- Requests made at or after the deadline are not created.
- Results depend on the chosen grid size and demand levels. Each configuration
  is averaged over only 5 seeds.
- The city map is drawn by `app.draw_city` from the model, because routes and
  planned stops are not single agents. Mesa's `make_space_component` is not
  used, so its zorder bug in 3.5.1 does not apply.
