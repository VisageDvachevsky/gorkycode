import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


@dataclass
class RoutePOI:
    id: int
    name: str
    lat: float
    lon: float
    avg_visit_minutes: int = 45
    rating: float = 0.0


class RoutePlanner:
    """Route optimisation using real-road metrics from 2GIS."""

    def __init__(self) -> None:
        self.walk_speed_kmh = settings.DEFAULT_WALK_SPEED_KMH

    def calculate_walk_time_minutes(self, distance_km: float) -> int:
        return int((distance_km / self.walk_speed_kmh) * 60) + 5

    async def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[RoutePOI],
        available_hours: float,
    ) -> Tuple[List[RoutePOI], float]:
        if not pois:
            return [], 0.0

        available_minutes = int(available_hours * 60)
        reordered = self._reorder_pois_by_sectors(start_lat, start_lon, pois)

        distance_matrix = await self._get_real_distance_matrix(
            start_lat,
            start_lon,
            reordered,
        )

        if distance_matrix is None:
            logger.warning("Distance Matrix API failed, using haversine fallback")
            return await self._optimize_route_haversine(
                start_lat,
                start_lon,
                reordered,
                available_hours,
            )

        route_indices, _, _ = self._greedy_nearest_neighbor(
            distance_matrix,
            reordered,
            available_minutes,
        )

        if not route_indices:
            return [], 0.0

        route_indices = self._two_opt_improve(
            route_indices,
            distance_matrix,
            reordered,
            available_minutes,
        )

        ordered_route = [reordered[i] for i in route_indices]

        total_distance = 0.0
        prev_idx = -1
        for idx in route_indices:
            total_distance += distance_matrix[prev_idx + 1][idx + 1]
            prev_idx = idx

        logger.info(
            "✓ Optimized route: %s POIs, %.2fkm (real roads)",
            len(ordered_route),
            total_distance,
        )
        return ordered_route, total_distance

    def _reorder_pois_by_sectors(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[RoutePOI],
    ) -> List[RoutePOI]:
        if len(pois) <= 3:
            return pois

        center_lat = sum(poi.lat for poi in pois) / len(pois)
        center_lon = sum(poi.lon for poi in pois) / len(pois)

        sectors = {"NE": [], "SE": [], "SW": [], "NW": []}
        for poi in pois:
            if poi.lat >= center_lat and poi.lon >= center_lon:
                sectors["NE"].append(poi)
            elif poi.lat < center_lat and poi.lon >= center_lon:
                sectors["SE"].append(poi)
            elif poi.lat < center_lat and poi.lon < center_lon:
                sectors["SW"].append(poi)
            else:
                sectors["NW"].append(poi)

        if start_lat >= center_lat and start_lon >= center_lon:
            start_sector = "NE"
        elif start_lat < center_lat and start_lon >= center_lon:
            start_sector = "SE"
        elif start_lat < center_lat and start_lon < center_lon:
            start_sector = "SW"
        else:
            start_sector = "NW"

        sector_priority = {
            "NE": ["SW", "SE", "NW", "NE"],
            "SE": ["NW", "NE", "SW", "SE"],
            "SW": ["NE", "NW", "SE", "SW"],
            "NW": ["SE", "SW", "NE", "NW"],
        }

        reordered: List[RoutePOI] = []
        for sector_key in sector_priority.get(start_sector, ["NE", "SE", "SW", "NW"]):
            reordered.extend(sectors[sector_key])

        if reordered:
            logger.info("✓ Reordered POIs by sectors (start: %s)", start_sector)
            return reordered

        return pois

    async def _get_real_distance_matrix(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[RoutePOI],
    ) -> Optional[np.ndarray]:
        all_points = [(start_lat, start_lon)] + [(poi.lat, poi.lon) for poi in pois]

        if len(all_points) > 10:
            logger.warning(
                "Too many POIs (%s) for Distance Matrix API (max 10 with free tier)",
                len(pois),
            )
            return None

        try:
            matrix_data = await twogis_client.get_distance_matrix(
                sources=all_points,
                targets=all_points,
                transport="pedestrian",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Distance Matrix API error: %s", exc)
            return None

        if not matrix_data:
            return None

        matrix = twogis_client.parse_distance_matrix(
            matrix_data,
            num_sources=len(all_points),
            num_targets=len(all_points),
        )
        return np.array(matrix)

    def _greedy_nearest_neighbor(
        self,
        distance_matrix: np.ndarray,
        pois: List[RoutePOI],
        available_minutes: int,
    ) -> Tuple[List[int], int, float]:
        n = len(pois)
        remaining = set(range(n))
        route: List[int] = []
        total_time = 0
        total_distance = 0.0
        current_idx = -1
        prev_direction: Optional[Tuple[float, float]] = None

        while remaining and total_time < available_minutes:
            best_idx = None
            best_score = float("inf")
            best_dist = None
            best_walk_time = 0.0
            best_poi_time = 0

            for poi_idx in remaining:
                dist = distance_matrix[current_idx + 1][poi_idx + 1]

                if not np.isfinite(dist):
                    continue

                walk_time = self.calculate_walk_time_minutes(dist)
                poi_time = pois[poi_idx].avg_visit_minutes

                if total_time + walk_time + poi_time > available_minutes:
                    continue

                score = dist

                if current_idx >= 0 and prev_direction is not None:
                    current_pos = (
                        pois[current_idx].lat,
                        pois[current_idx].lon,
                    )
                    next_pos = (
                        pois[poi_idx].lat,
                        pois[poi_idx].lon,
                    )
                    direction = (
                        next_pos[0] - current_pos[0],
                        next_pos[1] - current_pos[1],
                    )
                    dot = direction[0] * prev_direction[0] + direction[1] * prev_direction[1]
                    if dot < 0:
                        score *= 1.3

                if score < best_score:
                    best_score = score
                    best_idx = poi_idx
                    best_dist = dist
                    best_walk_time = walk_time
                    best_poi_time = poi_time

            if best_idx is None:
                break

            if current_idx >= 0:
                current_pos = (
                    pois[current_idx].lat,
                    pois[current_idx].lon,
                )
                next_pos = (
                    pois[best_idx].lat,
                    pois[best_idx].lon,
                )
                prev_direction = (
                    next_pos[0] - current_pos[0],
                    next_pos[1] - current_pos[1],
                )

            route.append(best_idx)
            total_time += best_walk_time + best_poi_time
            total_distance += best_dist if best_dist is not None else 0.0
            current_idx = best_idx
            remaining.remove(best_idx)

        return route, total_time, total_distance

    def _two_opt_improve(
        self,
        route: List[int],
        distance_matrix: np.ndarray,
        pois: List[RoutePOI],
        available_minutes: int,
        max_iterations: int = 10,
    ) -> List[int]:
        if len(route) < 4:
            return route

        improved = True
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(len(route) - 2):
                for j in range(i + 2, len(route)):
                    current_dist = self._route_segment_distance(route, i, j, distance_matrix)

                    new_route = route[: i + 1] + route[i + 1 : j + 1][::-1] + route[j + 1 :]
                    new_dist = self._route_segment_distance(new_route, i, j, distance_matrix)

                    if new_dist < current_dist:
                        new_time = self._calculate_total_time(new_route, distance_matrix, pois)
                        if new_time <= available_minutes:
                            route = new_route
                            improved = True
                            logger.debug("2-opt: improved by %.2fkm", current_dist - new_dist)

            if improved:
                logger.info("✓ 2-opt improved route in iteration %s", iteration)

        return route

    def _route_segment_distance(
        self,
        route: List[int],
        start_idx: int,
        end_idx: int,
        distance_matrix: np.ndarray,
    ) -> float:
        total = 0.0

        if start_idx == 0:
            total += distance_matrix[0][route[start_idx] + 1]
        else:
            total += distance_matrix[route[start_idx - 1] + 1][route[start_idx] + 1]

        for k in range(start_idx, min(end_idx, len(route) - 1)):
            total += distance_matrix[route[k] + 1][route[k + 1] + 1]

        return total

    def _calculate_total_time(
        self,
        route: List[int],
        distance_matrix: np.ndarray,
        pois: List[RoutePOI],
    ) -> int:
        total_time = 0
        prev_idx = -1

        for poi_idx in route:
            dist = distance_matrix[prev_idx + 1][poi_idx + 1]
            walk_time = self.calculate_walk_time_minutes(dist)
            poi_time = pois[poi_idx].avg_visit_minutes
            total_time += walk_time + poi_time
            prev_idx = poi_idx

        return total_time

    async def _optimize_route_haversine(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[RoutePOI],
        available_hours: float,
    ) -> Tuple[List[RoutePOI], float]:
        available_minutes = int(available_hours * 60)

        current_pos = (start_lat, start_lon)
        remaining_pois = list(pois)
        ordered_route: List[RoutePOI] = []
        total_time = 0
        total_distance = 0.0

        while remaining_pois and total_time < available_minutes:
            nearest_poi = None
            nearest_dist = float("inf")

            for poi in remaining_pois:
                dist = twogis_client.calculate_distance(
                    current_pos[0],
                    current_pos[1],
                    poi.lat,
                    poi.lon,
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_poi = poi

            if nearest_poi is None:
                break

            walk_time = self.calculate_walk_time_minutes(nearest_dist)
            poi_time = nearest_poi.avg_visit_minutes

            if total_time + walk_time + poi_time > available_minutes:
                break

            ordered_route.append(nearest_poi)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_pos = (nearest_poi.lat, nearest_poi.lon)
            remaining_pois.remove(nearest_poi)

        return ordered_route, total_distance


route_planner_engine = RoutePlanner()
