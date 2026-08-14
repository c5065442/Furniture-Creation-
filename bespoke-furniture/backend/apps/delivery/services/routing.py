"""
Order a set of delivery stops into an efficient route from a depot, using
real road-network travel times from Google's Distance Matrix API where
available, or a haversine-distance fake in tests/local dev.

Algorithm: nearest-neighbor construction + 2-opt local-search improvement.
Both are pure Python, deterministic, and small enough to unit test against
a hand-verifiable distance matrix -- a full solver (e.g. OR-Tools) would be
overkill for the 2-4 vans / a few dozen stops per week this system handles.
"""

import abc
from dataclasses import dataclass

import requests
from django.conf import settings

from .clustering import haversine_km


class DistanceMatrixError(Exception):
    pass


class DistanceMatrixClient(abc.ABC):
    @abc.abstractmethod
    def get_matrix(self, points: list[tuple[float, float]]) -> list[list[float]]:
        """Return an NxN matrix of travel time (minutes) between points, points[i] to points[j]."""


class GoogleDistanceMatrixClient(DistanceMatrixClient):
    ENDPOINT = "https://maps.googleapis.com/maps/api/distancematrix/json"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise DistanceMatrixError(
                "GOOGLE_MAPS_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )

    def get_matrix(self, points: list[tuple[float, float]]) -> list[list[float]]:
        locations = "|".join(f"{lat},{lng}" for lat, lng in points)
        response = requests.get(
            self.ENDPOINT,
            params={"origins": locations, "destinations": locations, "key": self.api_key},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "OK":
            raise DistanceMatrixError(f"Distance Matrix request failed: {payload.get('status')}")

        matrix = []
        for row in payload["rows"]:
            matrix_row = []
            for element in row["elements"]:
                if element.get("status") != "OK":
                    matrix_row.append(float("inf"))
                else:
                    matrix_row.append(element["duration"]["value"] / 60)  # seconds -> minutes
            matrix.append(matrix_row)
        return matrix


class FakeDistanceMatrixClient(DistanceMatrixClient):
    """Haversine-distance based fake, assuming an average 40km/h road speed."""

    AVG_SPEED_KMH = 40.0

    def get_matrix(self, points: list[tuple[float, float]]) -> list[list[float]]:
        matrix = []
        for lat1, lng1 in points:
            row = []
            for lat2, lng2 in points:
                distance_km = haversine_km(lat1, lng1, lat2, lng2)
                row.append((distance_km / self.AVG_SPEED_KMH) * 60)  # minutes
            matrix.append(row)
        return matrix


def nearest_neighbor_route(matrix: list[list[float]], start_index: int = 0) -> list[int]:
    n = len(matrix)
    visited = {start_index}
    route = [start_index]
    current = start_index
    while len(visited) < n:
        nearest = min(
            (i for i in range(n) if i not in visited),
            key=lambda i: matrix[current][i],
        )
        route.append(nearest)
        visited.add(nearest)
        current = nearest
    return route


def route_length(route: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[route[i]][route[i + 1]] for i in range(len(route) - 1))


def two_opt(route: list[int], matrix: list[list[float]]) -> list[int]:
    """Classic 2-opt: repeatedly reverse a segment if it shortens the route, until no improvement."""
    best = route[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                if route_length(candidate, matrix) < route_length(best, matrix):
                    best = candidate
                    improved = True
    return best


@dataclass
class RoutedStop:
    order_id: int
    sequence: int  # 1 = delivered first
    load_position: int  # 1 = loaded first => delivered last


@dataclass
class RouteResult:
    stops: list[RoutedStop]
    total_duration_min: float


def plan_route(
    depot: tuple[float, float],
    stop_points: list[tuple[int, float, float]],  # (order_id, lat, lng)
    client: DistanceMatrixClient | None = None,
) -> RouteResult:
    """
    stop_points excludes the depot; depot is always index 0 in the working
    matrix. Returns stops ordered by delivery sequence, with load_position
    computed as the reverse (last-loaded = first-delivered) for van packing.
    """
    if not stop_points:
        return RouteResult(stops=[], total_duration_min=0.0)

    client = client or FakeDistanceMatrixClient()
    points = [depot] + [(lat, lng) for _, lat, lng in stop_points]
    matrix = client.get_matrix(points)

    route_indices = nearest_neighbor_route(matrix, start_index=0)
    route_indices = two_opt(route_indices, matrix)

    # Drop the depot (index 0) from the delivery sequence, keep visiting order.
    delivery_order = [i for i in route_indices if i != 0]
    total_duration = route_length(route_indices, matrix)

    n = len(delivery_order)
    stops = []
    for sequence, matrix_index in enumerate(delivery_order, start=1):
        order_id = stop_points[matrix_index - 1][0]  # -1 because depot occupies index 0
        load_position = n - sequence + 1
        stops.append(RoutedStop(order_id=order_id, sequence=sequence, load_position=load_position))

    return RouteResult(stops=stops, total_duration_min=total_duration)
