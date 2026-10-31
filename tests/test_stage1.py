"""Stage 1: single-passenger taxis, arrivals, deadline handling."""

from agents import COMPLETED, NOT_COMPLETED
from helpers import make_model, run
from messages import ACCEPT, CONFIRM, PROPOSE, REQUEST
from model import TaxiModel, generate_scenario


def test_one_taxi_one_passenger_completes():
    # Taxi at (0,0); passenger at (3,0) going to (3,4), requested at minute 0.
    m = run(make_model([(0, 0)], [(0, (3, 0), (3, 4))], duration=20))
    p = m.passengers[0]
    assert p.status == COMPLETED
    assert p.pickup_time == 3  # 3 districts away, 1 minute each
    assert p.arrival_time == 7  # 4 more districts
    assert p.waiting_time == 3
    assert p.in_vehicle_time == 4
    assert p.total_time == 7
    assert p.extra_delay == 0
    assert m.taxis[0].distance == 7
    assert m.latest_metrics["completed"] == 1
    assert m.latest_metrics["waiting"] == 0
    assert m.latest_metrics["travelling"] == 0


def test_taxi_moves_one_cell_per_minute():
    m = make_model([(0, 0)], [(0, (5, 0), (5, 1))], duration=20)
    positions = []
    for _ in range(5):
        m.step()
        positions.append(m.taxis[0].pos)
    assert positions == [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]


def test_slower_taxi_speed_takes_longer():
    m = run(make_model([(0, 0)], [(0, (2, 0), (2, 2))], duration=30,
                       minutes_per_district=2))
    p = m.passengers[0]
    assert p.pickup_time == 4
    assert p.arrival_time == 8


def test_passenger_unserved_at_deadline():
    # Taxi far away: cannot reach the passenger in 5 minutes.
    m = run(make_model([(0, 0)], [(0, (10, 10), (12, 12))], duration=5))
    p = m.passengers[0]
    assert p.status == NOT_COMPLETED
    assert p.status_at_deadline == "assigned"
    assert p.arrival_time is None
    assert m.latest_metrics["completed"] == 0
    assert m.latest_metrics["not_completed"] == 1
    assert m.latest_metrics["completed_pct"] == 0


def test_passenger_travelling_at_deadline_not_completed():
    m = run(make_model([(0, 0)], [(0, (0, 0), (15, 0))], duration=10))
    p = m.passengers[0]
    assert p.pickup_time == 0
    assert p.status == NOT_COMPLETED
    assert p.status_at_deadline == "travelling"
    assert m.latest_metrics["completed"] == 0


def test_simulation_stops_at_duration():
    m = TaxiModel(num_taxis=3, num_passengers=20, duration=17, seed=4)
    steps = 0
    while m.running:
        m.step()
        steps += 1
        assert steps <= 17
    assert steps == 17
    assert m.minute == 17
    m.step()  # extra calls after the deadline change nothing
    assert m.minute == 17
    assert m.latest_metrics["waiting"] + m.latest_metrics["assigned"] == 0
    assert m.latest_metrics["travelling"] == 0


def test_capacity_one_serves_one_at_a_time():
    # Two passengers at the same place: the second must wait for the first trip.
    m = run(make_model([(0, 0)], [(0, (0, 0), (5, 0)), (0, (0, 0), (0, 5))]))
    p1, p2 = m.passengers
    assert p1.arrival_time == 5
    assert p2.pickup_time == 10  # back from (5,0) to (0,0)
    assert not p1.shared and not p2.shared


def test_nearest_taxi_wins():
    m = make_model([(0, 0), (9, 9)], [(0, (8, 8), (8, 0))])
    m.step()
    assert m.passengers[0].taxi is m.taxis[1]


def test_messages_follow_protocol():
    m = make_model([(0, 0), (5, 5)], [(0, (1, 1), (2, 2))])
    m.step()
    counts = m.message_counts
    assert counts[REQUEST] == 2  # one CFP per taxi
    assert counts[PROPOSE] == 2
    assert counts[ACCEPT] == 1
    assert counts[CONFIRM] == 1


def test_all_at_start_arrivals():
    m = TaxiModel(num_passengers=15, arrival_mode="all_at_start", seed=2)
    assert len(m.passengers) == 15
    assert all(p.request_time == 0 for p in m.passengers)


def test_gradual_arrivals_appear_over_time():
    m = TaxiModel(num_passengers=30, arrival_mode="gradual", arrival_window=40,
                  duration=60, seed=2)
    created_before = len(m.passengers)
    run(m)
    assert created_before < 30
    assert len(m.passengers) == 30
    times = [p.request_time for p in m.passengers]
    assert min(times) >= 0 and max(times) < 40


def test_same_seed_same_demand_across_configurations():
    a = generate_scenario(7, 20, 20, 5, 40, "gradual", 90)
    b = generate_scenario(7, 20, 20, 10, 60, "gradual", 90)
    c = generate_scenario(7, 20, 20, 5, 40, "all_at_start", 90)
    assert a[1] == b[1][:40]  # same first 40 passengers
    assert a[0] == b[0][:5]  # same first 5 taxi positions
    assert [r[1:] for r in a[1]] == [r[1:] for r in c[1]]  # same trips


def test_model_is_reproducible():
    def final(seed):
        m = run(TaxiModel(num_passengers=30, sharing_mode="detour", capacity=2,
                          seed=seed))
        return str(m.latest_metrics)  # str() so NaN values compare equal

    assert final(5) == final(5)
