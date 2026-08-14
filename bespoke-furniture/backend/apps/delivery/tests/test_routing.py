from apps.delivery.services.routing import (
    FakeDistanceMatrixClient,
    nearest_neighbor_route,
    plan_route,
    route_length,
    two_opt,
)

# A small hand-verifiable distance matrix: 4 points on a line at 0, 1, 2, 10.
# Depot (index 0) -> the optimal tour visiting 1, 2, 3 in order is 0-1-2-3
# (length 10), vs. e.g. 0-3-1-2 which would be far longer.
LINE_MATRIX = [
    [0, 1, 2, 10],
    [1, 0, 1, 9],
    [2, 1, 0, 8],
    [10, 9, 8, 0],
]


class TestNearestNeighborAndTwoOpt:
    def test_nearest_neighbor_visits_closest_points_first(self):
        route = nearest_neighbor_route(LINE_MATRIX, start_index=0)
        assert route == [0, 1, 2, 3]

    def test_two_opt_does_not_worsen_an_already_optimal_route(self):
        route = nearest_neighbor_route(LINE_MATRIX, start_index=0)
        improved = two_opt(route, LINE_MATRIX)
        assert route_length(improved, LINE_MATRIX) <= route_length(route, LINE_MATRIX)

    def test_two_opt_improves_a_deliberately_bad_route(self):
        bad_route = [0, 3, 1, 2]  # visits the far point second -- clearly suboptimal
        improved = two_opt(bad_route, LINE_MATRIX)
        assert route_length(improved, LINE_MATRIX) < route_length(bad_route, LINE_MATRIX)
        assert route_length(improved, LINE_MATRIX) == route_length([0, 1, 2, 3], LINE_MATRIX)


class TestPlanRoute:
    def test_empty_stops_returns_empty_result(self):
        result = plan_route(depot=(53.38, -1.47), stop_points=[])
        assert result.stops == []
        assert result.total_duration_min == 0.0

    def test_load_position_is_reverse_of_delivery_sequence(self):
        depot = (0.0, 0.0)
        stops = [(101, 0.0, 0.01), (102, 0.0, 0.02), (103, 0.0, 0.03)]
        result = plan_route(depot, stops, client=FakeDistanceMatrixClient())

        n = len(result.stops)
        for stop in result.stops:
            assert stop.load_position == n - stop.sequence + 1

        sequences = sorted(stop.sequence for stop in result.stops)
        assert sequences == list(range(1, n + 1))

    def test_all_order_ids_present_exactly_once(self):
        depot = (0.0, 0.0)
        stops = [(1, 0.0, 0.05), (2, 0.0, 0.01), (3, 0.0, 0.03)]
        result = plan_route(depot, stops, client=FakeDistanceMatrixClient())
        assert sorted(stop.order_id for stop in result.stops) == [1, 2, 3]
