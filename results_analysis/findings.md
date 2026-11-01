# Findings (30x30 base, seeds 1-10, mean ± std)

Sources: `results_sweep/summary.csv` (load sweep: 20 taxis, 30-180 passengers),
`results_fleet/` (90 passengers, varying fleet),
`results_analysis/fleet_equivalence.csv`, and `results/` (S1-S12).
Charts: `results_analysis/sweep.png`, `results_analysis/fleet.png`.

Distances are counted in districts driven. "Taxi distance" covers taxis only;
"vehicle distance" = taxi distance + bus distance, summed per run. Buses drive
their full lines whatever their load (1413.6 ± 5.5 districts per run in every
bus scenario without congestion), so whenever buses are on, the vehicle
distance is much larger than the taxi distance. A bus is a bigger vehicle than
a taxi, so a bus district is not directly comparable to a car district for
pollution or road space; the totals below count vehicle movements only.

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
- **Sharing saves taxis and driving for the same service.** Reaching the S1
  level (58.3 %) takes 20 taxis without sharing and 12 with detour sharing
  (59.8 ± 4.2 %): 8 fewer taxis (-40 %). Taxi distance falls from 2066.9 ± 51.1
  to 1219.1 ± 23.9 districts (-41.0 %) and the empty share from 45.3 ± 2.6 % to
  24.0 ± 3.3 %. There are no buses here, so this is also the whole vehicle
  distance.
- **With buses, total driving is higher, not lower.** Sharing plus buses needs
  only 10 taxis for the S1 level (58.7 ± 3.6 %, 10 fewer than single rides),
  and the taxis drive 1023.2 ± 26.3 districts.
  But the buses add 1413.6 ± 5.5, so the vehicle distance is 2436.8 ± 27.7:
  18 % more than single rides (2066.9 ± 51.1) and twice that of sharing
  without buses (1219.1 ± 23.9). At this demand the buses drive their full
  lines while carrying only about 0.13 passengers per district.
- **85 % service is out of reach without sharing.** Single rides reach only
  81.9 ± 5.4 % with 30 taxis (2666.8 ± 143.6 districts driven). Detour sharing
  reaches 85 % with 20 taxis (86.3 ± 2.7 %, 1783.7 ± 81.8 districts, empty share
  20.5 ± 1.2 %). With buses 18 taxis suffice (85.3 ± 3.3 %), and they drive
  1604.0 ± 82.3 districts, but with the buses' 1413.6 ± 5.5 the vehicle distance
  is 3017.6 ± 84.4: the highest of the three at this service level.
- **Waiting vs in-vehicle trade-off.** At 90 passengers, sharing halves the wait
  (10.0 ± 1.4 vs 21.6 ± 3.3 min) and adds 3.9 min in the vehicle (24.8 ± 1.1
  vs 20.9 ± 0.9 min; extra delay 3.9 ± 0.2), so the total journey is 7.7 min
  shorter (34.8 ± 2.3 vs 42.5 ± 3.7). Extra delay grows with load (1.2 ± 0.4 min
  at 30 passengers, 4.8 ± 0.2 at 180) but stays far below the 10-minute limit.
- **Walking to a neighbour district** (S5 vs S4) gives a small gain: completed
  88.7 ± 4.9 % vs 86.3 ± 2.7 %, wait 8.7 ± 1.1 vs 10.0 ± 1.4 min, empty share
  17.6 ± 1.9 % vs 20.5 ± 1.2 %.
- **Buses relieve the taxis, but add more driving than they save.** About
  15.8 ± 3.7 % of passengers take the bus. Without sharing, completion rises
  from 58.3 ± 3.3 % (S1) to 67.7 ± 5.0 % (S7); with sharing only from 86.3 ± 2.7 %
  (S4) to 88.1 ± 2.9 % (S6). Taxi distance per completed passenger falls (S6:
  20.6 ± 1.3 vs S4: 23.0 ± 0.8), but counting the buses, vehicle distance per
  completed passenger rises: S6 drives 1634.9 ± 103.7 taxi + 1413.6 ± 5.5 bus =
  3048.5 ± 106.8 districts (38.5 ± 1.6 per completed passenger, vs 23.0 ± 0.8 in
  S4); S7 drives 2023.4 ± 76.9 + 1413.6 ± 5.5 = 3437.0 ± 77.7 (56.8 ± 4.6 per
  completed, vs 39.5 ± 2.1 in S1). Buses carry 0.13 ± 0.03 passengers per
  district. Bus riders also wait longer than taxi riders (19.0 ± 2.6 vs 8.8 ±
  1.5 min in S6, the walk to the stop included).
- **Congestion is the largest loss.** Completion falls from 86.3 ± 2.7 % to
  69.4 ± 5.0 % with sharing (S4 → S8) and from 58.3 ± 3.3 % to 40.8 ± 2.4 % without
  (S1 → S9); total journey time rises to 42.6 ± 2.5 and 49.6 ± 4.1 min.
  Sharing keeps relatively more of its service (-20 % vs -30 %).
- **Patience changes which offers are taken.** A patient passenger ignores any
  offer whose pickup would come after its patience runs out, so idle taxis are
  no longer sent on long empty drives (abandoning passengers never held a
  taxi). Without sharing, 26.7 ± 3.2 % abandon, but the empty share falls from
  45.3 ± 2.6 % to 31.8 ± 2.5 % and taxi distance per completed passenger from
  39.5 ± 2.1 to 31.0 ± 1.9, so completion rises to 66.8 ± 3.8 % (S11 vs 58.3 % in
  S1) and the wait falls to 12.6 ± 1.0 min. With sharing almost everyone is
  confirmed in the first round, so patience only removes passengers whose
  offers came too late: 10.8 ± 4.4 % abandon, completion falls to 81.0 ± 3.9 %
  and acceptable trips to 78.1 ± 3.1 % (S10 vs 86.3 ± 2.7 % in S4).
- **All four features together** (S12) complete 75.8 ± 5.4 %, between S4 and the
  congestion-only S8. Its taxis drive the least per completed passenger of
  S1-S12 (19.9 ± 1.7 districts; empty share 17.0 ± 2.3 %), but adding the buses
  (1217.9 ± 4.6 districts, fewer than elsewhere because congestion slows them)
  gives 1350.9 ± 87.6 + 1217.9 ± 4.6 = 2568.8 ± 89.8 vehicle districts, i.e.
  37.8 ± 2.8 per completed passenger, against 25.7 ± 1.9 for S8 (sharing with
  congestion, no buses).
