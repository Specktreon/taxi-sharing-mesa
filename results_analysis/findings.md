# Findings (30x30 base, seeds 1-10, mean ± std)

Sources: `results_sweep/summary.csv` (load sweep: 20 taxis, 30-180 passengers),
`results_fleet/summary.csv` (90 passengers, varying fleet),
`results_analysis/fleet_equivalence.csv`, and `results/summary.csv` (S1-S12).
Charts: `results_analysis/sweep.png`, `results_analysis/fleet.png`.

- **Sharing helps most at medium-to-high load.** With 20 taxis, detour sharing
  (capacity 4) completes 86.3 ± 2.7 % of 90 passengers against 58.3 ± 3.3 %
  for single rides (+28.0 points), and 72.8 ± 2.9 % against 44.4 ± 2.9 % at
  120 passengers (+28.4). At 180 passengers it still serves 55.3 ± 3.1 % against
  30.3 ± 1.6 %, i.e. 1.8 times as many.
- **At low load sharing stops helping.** With 30 passengers both serve almost
  everyone (93.7 ± 2.3 % vs 93.7 ± 3.1 %), and the total journey time is no
  better (27.9 ± 2.2 vs 27.6 ± 2.1 min): the 1.2 ± 0.4 min of extra delay
  cancels the shorter wait (5.3 ± 1.2 vs 6.1 ± 1.3 min).
- **Capacity 4 adds little over capacity 2** until demand is very high: 86.3 ±
  2.7 % vs 84.0 ± 3.1 % at 90 passengers, 55.3 ± 3.1 % vs 48.7 ± 2.5 % at 180.
  With 1-minute stops, every extra rider costs the others time, so the
  10-minute extra-delay limit blocks most third and fourth riders.
- **Sharing saves taxis for the same service.** Reaching the S1 level (58.3 %)
  takes 20 taxis without sharing, 12 with detour sharing (59.8 ± 4.2 %), and 10
  with detour sharing plus buses (58.7 ± 3.6 %): 8 and 10 fewer taxis (40 % and
  50 %).
- **...and removes a large part of the driving.** At that same service level,
  total taxi distance falls from 2066.9 ± 51.1 districts (none, 20 taxis) to
  1219.1 ± 23.9 (detour, 12 taxis; -41 %) and 1023.2 ± 26.3 (detour + buses,
  10 taxis; -50.5 %). The empty share drops from 45.3 ± 2.6 % to 24.0 ± 3.3 % and
  25.4 ± 3.5 %.
- **85 % service is out of reach without sharing.** Single rides reach only
  81.9 ± 5.4 % with 30 taxis (2666.8 districts driven). Detour sharing reaches
  85 % with 20 taxis (86.3 ± 2.7 %, 1783.7 ± 81.8 districts, empty share 20.5 ±
  1.2 %), and with buses 18 taxis suffice (85.3 ± 3.3 %, 1604.0 ± 82.3
  districts, 22.0 ± 3.0 %).
- **Waiting vs in-vehicle trade-off.** At 90 passengers, sharing halves the wait
  (10.0 ± 1.4 vs 21.6 ± 3.3 min) and adds 3.9 min in the vehicle (24.8 ± 1.1
  vs 20.9 ± 0.9 min; extra delay 3.9 ± 0.2), so the total journey is 7.7 min
  shorter (34.8 ± 2.3 vs 42.5 ± 3.7). Extra delay grows with load (1.2 ± 0.4 min
  at 30 passengers, 4.8 ± 0.2 at 180) but stays far below the 10-minute limit.
- **Walking to a neighbour district** (S5 vs S4) gives a small gain: completed
  88.7 ± 4.9 % vs 86.3 ± 2.7 %, wait 8.7 ± 1.1 vs 10.0 ± 1.4 min, empty share
  17.6 ± 1.9 % vs 20.5 ± 1.2 %.
- **Buses relieve the taxis most when taxis do not share.** About 15.8 ± 3.7 % of
  passengers take the bus. Without sharing, completion rises from 58.3 ± 3.3 %
  (S1) to 67.7 ± 5.0 % (S7); with sharing only from 86.3 ± 2.7 % (S4) to 88.1 ±
  2.9 % (S6), but taxi distance per completed passenger falls from 23.0 ± 0.8 to
  20.6 ± 1.3. Bus riders wait longer than taxi riders (19.0 ± 2.6 vs 8.8 ± 1.5
  min in S6, the walk to the stop included), and buses run mostly empty (0.13 ±
  0.03 passengers per bus-district).
- **Congestion is the largest loss.** Completion falls from 86.3 ± 2.7 % to
  69.4 ± 5.0 % with sharing (S4 → S8) and from 58.3 ± 3.3 % to 40.8 ± 2.4 % without
  (S1 → S9); total journey time rises to 42.6 ± 2.5 and 49.6 ± 4.1 min.
  Sharing keeps relatively more of its service (-20 % vs -30 %).
- **Patience changes who is served.** Without sharing, 26.7 ± 3.2 % of passengers
  abandon, which frees taxis: completion rises to 66.8 ± 3.8 % (S11 vs 58.3 % in
  S1) and the wait falls to 12.6 ± 1.0 min. With sharing, 10.8 ± 4.4 % abandon,
  completion falls to 81.0 ± 3.9 % and acceptable trips to 78.1 ± 3.1 % (S10 vs
  86.3 ± 2.7 % in S4).
- **All four features together** (S12) complete 75.8 ± 5.4 %, between S4 and the
  congestion-only S8, with the lowest taxi distance per completed passenger of
  S1-S12 (19.9 ± 1.7 districts) and an empty share of 17.0 ± 2.3 %.
