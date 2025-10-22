"""Route optimisation helpers (nearest neighbour, dynamic programming, 2-opt)."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple, TypeVar

from .geometry import haversine_km

T = TypeVar("T")


def _safe_float(value, fallback: float) -> float:
    try:
        if value is None:
            raise TypeError
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _extract_points(pois: Sequence[T], start_lat: float, start_lon: float) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for poi in pois:
        lat = None
        lon = None
        if hasattr(poi, "lat"):
            lat = getattr(poi, "lat")
        elif isinstance(poi, dict):
            lat = poi.get("lat")
        if hasattr(poi, "lon"):
            lon = getattr(poi, "lon")
        elif isinstance(poi, dict):
            lon = poi.get("lon")
        points.append((_safe_float(lat, start_lat), _safe_float(lon, start_lon)))
    return points


def optimize_poi_sequence(
    pois: Sequence[T],
    start_lat: float,
    start_lon: float,
    *,
    max_iterations: int = 100,
) -> List[T]:
    """Optimise POI visit order using heuristics tuned for small itineraries."""

    entries = list(pois)
    if len(entries) <= 1:
        return entries[:]

    start = (float(start_lat), float(start_lon))
    points = _extract_points(entries, start[0], start[1])
    count = len(entries)

    if count <= 7:
        order = _dynamic_programming_order(start, points)
    else:
        order = _nearest_neighbor_order(start, points)
        if count <= 15:
            order = _two_opt(order, start, points, max_iterations=max(10, max_iterations))
        else:
            order = _two_opt(order, start, points, max_iterations=max(5, max_iterations // 2 or 1))

    return [entries[idx] for idx in order]


def _nearest_neighbor_order(start: Tuple[float, float], points: Sequence[Tuple[float, float]]) -> List[int]:
    remaining = set(range(len(points)))
    order: List[int] = []
    current = start
    while remaining:
        nearest_idx = min(
            remaining,
            key=lambda idx: haversine_km(
                current[0],
                current[1],
                points[idx][0],
                points[idx][1],
            ),
        )
        order.append(nearest_idx)
        remaining.remove(nearest_idx)
        current = points[nearest_idx]
    return order


def _two_opt(
    order: List[int],
    start: Tuple[float, float],
    points: Sequence[Tuple[float, float]],
    *,
    max_iterations: int,
) -> List[int]:
    if len(order) < 4 or max_iterations <= 0:
        return order

    best_order = order[:]
    best_distance = _route_length(best_order, start, points)
    iteration = 0
    improved = True

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, len(best_order) - 2):
            for j in range(i + 1, len(best_order)):
                if j - i == 1:
                    continue
                new_order = best_order[:]
                new_order[i:j] = reversed(best_order[i:j])
                new_distance = _route_length(new_order, start, points)
                if new_distance + 1e-9 < best_distance:
                    best_order = new_order
                    best_distance = new_distance
                    improved = True
                    break
            if improved:
                break
    return best_order


def _route_length(order: Sequence[int], start: Tuple[float, float], points: Sequence[Tuple[float, float]]) -> float:
    total = 0.0
    current = start
    for idx in order:
        point = points[idx]
        total += haversine_km(current[0], current[1], point[0], point[1])
        current = point
    return total


def _dynamic_programming_order(
    start: Tuple[float, float], points: Sequence[Tuple[float, float]]
) -> List[int]:
    n = len(points)
    if n <= 1:
        return list(range(n))

    dist_start = [haversine_km(start[0], start[1], point[0], point[1]) for point in points]
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dist[i][j] = haversine_km(points[i][0], points[i][1], points[j][0], points[j][1])

    size = 1 << n
    dp = [[math.inf] * n for _ in range(size)]
    parent = [[-1] * n for _ in range(size)]

    for i in range(n):
        dp[1 << i][i] = dist_start[i]

    for mask in range(size):
        for last in range(n):
            if not (mask & (1 << last)):
                continue
            current_cost = dp[mask][last]
            if current_cost == math.inf:
                continue
            for nxt in range(n):
                if mask & (1 << nxt):
                    continue
                new_mask = mask | (1 << nxt)
                new_cost = current_cost + dist[last][nxt]
                if new_cost < dp[new_mask][nxt]:
                    dp[new_mask][nxt] = new_cost
                    parent[new_mask][nxt] = last

    mask = size - 1
    last = min(range(n), key=lambda idx: dp[mask][idx])
    order: List[int] = []
    while last != -1:
        order.append(last)
        prev = parent[mask][last]
        mask &= ~(1 << last)
        last = prev

    order.reverse()
    return order


__all__ = ["optimize_poi_sequence"]
