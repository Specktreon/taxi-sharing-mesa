# Report outline (5-10 pages)

Write the results only from `results/summary.csv`, `results/runs.csv` and
`results/charts/`. Re-run `python run_experiments.py` if anything in the code or
`experiments.csv` changes, and update the numbers.

## 1. Introduction (~0.5 page)
- Context: urban taxis, shared rides, the trade-off between serving more people
  and extra travel time for each passenger; buses as the fixed-route
  alternative.
- Research question (verbatim from the README).
- Why an agent-based model: decentralised taxi/passenger decisions, local
  interaction through messages, heterogeneous passengers (mode, patience).

## 2. Model design (~2 pages)
- Environment: 30x30 `MultiGrid`, districts, one step = one minute, x-first
  Manhattan routes; the fixed study settings (README §4 table) and why they are
  fixed.
- Agents: TaxiAgent, PassengerAgent and BusAgent attributes and states. A state
  diagram per agent type is useful (passenger: waiting → assigned → travelling
  → completed, plus abandoned / not_completed; bus passenger: to stop → at stop
  → riding → to destination).
- Interaction protocol: REQUEST / PROPOSE / ACCEPT / CONFIRM-REJECT. Include a
  sequence diagram and note its similarity to the Contract Net Protocol.
- Step phases and Mesa scheduling (`agents_by_type[...].do`).
- Gradual arrivals over 90 minutes, the 120-minute deadline (not completed).

## 3. Sharing rules (~1-1.5 pages)
- Stages 1-4 as incremental design: single passenger; two passengers without a
  route change; route change with several stops (general insertion); several
  passengers (capacity up to 4).
- Boarding time at every stop, timing definitions, the individual baseline
  (2 x boarding + direct drive): a solo trip has extra delay 0.
- `MAX_EXTRA_DELAY_MINUTES = 10`, the extra-delay definition, the promise rule;
  why the threshold is fixed.
- Worked example with the deterministic scenarios in `tests/test_sharing.py`
  and `tests/test_stage4.py` (accepted / rejected insertions, promise rule).
- Insertion search: all (i, j) positions, existing order kept; cost; booking
  limit 2 x capacity and why it is needed.

## 4. The four features (~1.5 pages)
- **Walking** to a neighbouring district: candidate pickup districts, "the
  walker gets there first" rule, why extra delay is measured from the pickup
  district and waiting time includes the walk.
- **Buses**: line layout (rows/columns at 1/3 and 2/3), stops, back-and-forth
  service, capacity; the mode-choice rule (both ends within 2 districts of
  stops on one line, least walking, no transfers); the bus journey.
- **Congestion**: centre one third of the grid x3, ring x2; integer costs;
  planning uses the same costs as movement (estimates stay exact, progress
  credit); routes do not avoid congestion.
- **Patience**: 10-30 min, separate seeded draw; ignoring proposals beyond
  patience; abandonment only before CONFIRM; `acceptable_pct`.

## 5. Implementation and verification (~1 page)
- Module structure (README §3).
- Metric definitions (README §7): waiting vs in-vehicle time, per-mode
  metrics, why extra delay is taxi-only, why the completed count/% is shown
  next to every average.
- Tests: what they check (hand-computed scenarios, invariants after every
  step, "every feature off reproduces the stored S1-S4 results exactly",
  bus capacity, walking never makes a taxi wait, estimates exact under
  congestion) and the number passed (`python -m pytest`).
- Visualization: `docs/grid_example.png` (S12, minute 40) with the legend
  sections; `docs/map_S1.png`, `docs/map_S6.png` for comparison.

## 6. Experimental setup (~1 page)
- Calibration of the base scenario (README §8 table): 20 taxis, 90 passengers,
  S1 ≈ 58 % completed.
- Table of the 12 scenarios S1-S12 (`experiments.csv`) and the fixed settings.
- 10 seeds per scenario, with identical demand and taxi start cells per seed
  across scenarios.
- Comparison groups:
  - sharing level: S1-S2-S3-S4;
  - each feature added to S4: S5 (walking), S6 (buses), S8 (congestion),
    S10 (patience);
  - the same features added to S1: S7, S9, S11 (does the feature matter more
    without sharing?);
  - everything together: S12 vs S4.

## 7. Results (~2 pages)
- `results/charts/comparison.png` and a results table, mean ± std over 10
  seeds (README §8 holds the current numbers):
  - completed %;
  - waiting time and total journey time (completed);
  - extra delay (taxi passengers);
  - taxi distance per completed passenger and empty distance share;
  - bus share, and per-mode completed % / times for S6, S7, S12;
  - acceptable % and abandoned % for S10-S12.
- Report numbers only as produced by the runs; always give the completed % next
  to averages.

## 8. Discussion (~1-1.5 pages)
- Answer the research question per metric: detour sharing (S3/S4) serves far
  more passengers than S1 with shorter waits, at a few minutes of extra delay;
  `no_detour` (S2) almost never triggers on random trips; capacity 4 adds
  little over 2 with 1-minute stops.
- Walking: small gains in completion and wait (S5 vs S4).
- Buses: few passengers qualify under the walking rule (~5 %), so totals barely
  change, but bus riders complete well; very low bus occupancy. Discuss the
  rule and the fixed lines.
- Congestion: the largest loss (S8, S9); sharing keeps more of its benefit than
  single rides.
- Patience: abandonment frees taxis, so completion can rise without sharing
  (S11 vs S1) while acceptable % falls with sharing (S10 vs S4); explain via
  `acceptable_pct`.
- Traffic and pollution through proxies only: taxi distance per passenger,
  empty share, occupancy; bus-km are not car-km. Make no claims about measured
  pollution or congestion.

## 9. Limitations and future work (~0.5 page)
- README §9: abstract grid; greedy assignment; no reordering of existing stops;
  booking limit; fixed boarding time; no repositioning; congestion fixed and
  not avoided by routing; bus lines fixed, no transfers, one-shot mode choice;
  patience only before CONFIRM; one adjacent walking district.
- Possible extensions: congestion-aware routing, reordering stops,
  repositioning, reassignment, bus transfers and a cost-based mode choice.

## 10. Conclusion (~0.25 page)

## Appendix (optional)
- How to run (README §2); full `summary.csv`.
