# Report outline (5-10 pages)

Write the results only from `results/summary.csv`, `results/runs.csv` and
`results/charts/`. Re-run `python run_experiments.py` if anything in the code or
`experiments.csv` changes.

## 1. Introduction (~0.5 page)
- Context: urban taxis, shared rides, trade-off between serving more people and
  extra travel time for each passenger.
- Research question (verbatim from the README).
- Why an agent-based model: decentralised taxi/passenger decisions, local
  interaction through messages.

## 2. Model design (~1.5-2 pages)
- Environment: `MultiGrid`, districts, one step = one minute, Manhattan routes,
  `MINUTES_PER_DISTRICT`.
- Agents: TaxiAgent and PassengerAgent attributes and states. A state diagram
  for each is useful.
- Interaction protocol: REQUEST / PROPOSE / ACCEPT / CONFIRM-REJECT. Include a
  sequence diagram and note its similarity to the Contract Net Protocol.
- Step phases and Mesa scheduling (`agents_by_type[...].do`).
- Passenger arrivals (all at start vs gradual) and the deadline rule (not
  completed).

## 3. Sharing rules (~1-1.5 pages)
- Stages 1-4 as incremental design (teacher's methodology):
  - single passenger;
  - two passengers without a route change;
  - route change with multiple stops (general insertion);
  - several passengers (capacity up to 4).
- Delay when reaching a passenger: `boarding_minutes` at every stop, the
  timing definitions (pickup = taxi reaches origin, arrival = alighting ends),
  and the individual baseline (2 x boarding + direct drive). A solo trip has
  extra delay 0.
- `MAX_EXTRA_DELAY_MINUTES` and the extra-delay definition. Explain why the
  threshold is fixed.
- Acceptability: the extra in-vehicle delay limit plus the promise rule
  (assigned pickups never slip more than 10 minutes).
- Worked example A→C with B→D, using the deterministic test scenarios in
  `tests/test_sharing.py` and `tests/test_stage4.py`:
  - delay 4 → accepted;
  - delay 16 → rejected; the passenger is booked after P1 instead;
  - destination detour, delay 8 → accepted;
  - insertion while driving to the first pickup;
  - promise rule rejection.
- Insertion search: all (i, j) positions, existing order kept; cost; booking
  limit 2 x capacity and why it is needed.

## 4. Implementation and verification (~1 page)
- Module structure (README §3).
- Metric definitions (README §6), especially the separation of waiting and
  in-vehicle time, and why the completed count is shown next to each average.
- Test list and what each test checks (`python -m pytest`, number passed).
- Visualization screenshot with legend: `docs/grid_example.png`, showing
  routes, ▲/▼ stops, and k/c labels.

## 5. Experimental setup (~1 page)
- Table of the 10 configurations (`experiments.csv`) and the fixed parameters.
- 5 seeds per configuration, with the same demand and taxi start cells per seed.
- Comparison pairs:
  - capacity / sharing mode: C1-C2-C3 and C4-C5-C6;
  - fleet size: C7-C8 vs C4-C6;
  - demand: C9-C10 vs C4-C6;
  - arrival mode: C1-C3 vs C4-C6. These differ in duration too; say so.

## 6. Results (~2 pages)
- `results/charts/comparison.png`, plus a results table: mean ± std of
  - completed (count and %);
  - waiting time;
  - total journey time;
  - extra delay;
  - distance per completed passenger;
  - empty distance share;
  - average occupancy (passenger distance ÷ taxi distance);
  - utilization.
- Report the numbers only as produced by the runs. Always show the completed
  count next to averages.

## 7. Discussion (~1-1.5 pages)
- Answer the research question per metric, with reference to the table.
- When does sharing help most (load level, fleet size, arrival pattern)?
- Why no_detour sharing rarely triggers on random trips.
- Trade-off between extra delay and waiting time.
- Traffic and pollution, through proxies only:
  - vehicle distance vs passenger distance;
  - empty share;
  - occupancy.
  Make no claims about measured pollution or congestion.
- Acceptability: extra delay and promise slips stay within 10 minutes by
  construction. Discuss what passengers gain (shorter wait) against what they
  give up (longer ride).

## 8. Limitations and future work (~0.5 page)
- README §8:
  - abstract grid;
  - greedy assignment;
  - insertion without reordering existing stops;
  - booking limit;
  - fixed boarding time;
  - no repositioning;
  - 5 seeds.
- Possible extensions: reordering existing stops, taxi repositioning,
  reassignment, bidding among taxis.

## 9. Conclusion (~0.25 page)

## Appendix (optional)
- How to run (README §2); full `summary.csv`.
