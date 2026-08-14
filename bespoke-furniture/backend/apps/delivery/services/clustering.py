"""
Group candidate orders into geographic clusters for van assignment.

Two stages, cheapest first:
  1. Free pre-filter: group by UK postcode "district" (the part of the
     postcode before the space, e.g. "S10" from "S10 2TN") -- no API calls.
  2. Greedy radius-based clustering on cached lat/lng (haversine distance),
     targeting a cluster count close to the number of available vans.

Pure Python, deterministic, and testable against fixed coordinates -- no ML
dependency, which would be overkill for a handful of clusters per week.
"""

import math
import re
from dataclasses import dataclass, field

POSTCODE_DISTRICT_RE = re.compile(r"^([A-Z]{1,2}\d[A-Z\d]?)", re.IGNORECASE)

EARTH_RADIUS_KM = 6371.0


def postcode_district(postcode: str) -> str:
    """'S10 2TN' -> 'S10'; falls back to the raw postcode if unparseable."""
    match = POSTCODE_DISTRICT_RE.match(postcode.strip())
    return match.group(1).upper() if match else postcode.strip().upper()


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class GeoPoint:
    """A clusterable candidate: order id + its delivery coordinates."""

    order_id: int
    postcode: str
    latitude: float
    longitude: float


@dataclass
class Cluster:
    points: list[GeoPoint] = field(default_factory=list)

    @property
    def order_ids(self) -> list[int]:
        return [p.order_id for p in self.points]

    @property
    def centroid(self) -> tuple[float, float]:
        n = len(self.points)
        return (sum(p.latitude for p in self.points) / n, sum(p.longitude for p in self.points) / n)


def group_by_postcode_district(points: list[GeoPoint]) -> dict[str, list[GeoPoint]]:
    groups: dict[str, list[GeoPoint]] = {}
    for point in points:
        groups.setdefault(postcode_district(point.postcode), []).append(point)
    return groups


def cluster_points(points: list[GeoPoint], target_cluster_count: int) -> list[Cluster]:
    """
    Two-stage clustering:
      1. Pre-group by postcode district (free, no API calls).
      2. Greedily merge district groups into `target_cluster_count` clusters
         by nearest-centroid distance, so the final cluster count matches
         the number of available vans for the run.
    """
    if not points:
        return []
    target_cluster_count = max(1, min(target_cluster_count, len(points)))

    district_groups = group_by_postcode_district(points)
    clusters = [Cluster(points=group) for group in district_groups.values()]

    # Merge smallest/nearest clusters together until we hit the target count.
    while len(clusters) > target_cluster_count:
        best_pair = None
        best_distance = math.inf
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                lat1, lng1 = clusters[i].centroid
                lat2, lng2 = clusters[j].centroid
                distance = haversine_km(lat1, lng1, lat2, lng2)
                if distance < best_distance:
                    best_distance = distance
                    best_pair = (i, j)
        i, j = best_pair
        clusters[i].points.extend(clusters[j].points)
        del clusters[j]

    return clusters
