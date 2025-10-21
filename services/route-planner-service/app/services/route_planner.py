from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import grpc
import numpy as np
from geopy.distance import geodesic

from app.core.config import settings
from app.proto import route_pb2, route_pb2_grpc
from app.services.transit import transit_advisor
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


CoordinateTuple = Tuple[float, float]


class RoutePlannerServicer(route_pb2_grpc.RoutePlannerServiceServicer):
    CLUSTER_DISTANCE_BY_INTENSITY: Dict[str, float] = {
        "relaxed": 0.4,
        "medium": 0.3,
        "intense": 0.22,
    }

    INTENSITY_PROFILES: Dict[str, Dict[str, float]] = {
        "relaxed": {
            "walk_speed_multiplier": 0.85,
            "visit_duration_multiplier": 1.3,
            "min_visit_minutes": 25,
            "max_visit_minutes": 75,
        },
        "medium": {
            "walk_speed_multiplier": 1.0,
            "visit_duration_multiplier": 1.0,
            "min_visit_minutes": 20,
            "max_visit_minutes": 60,
        },
        "intense": {
            "walk_speed_multiplier": 1.15,
            "visit_duration_multiplier": 0.75,
            "min_visit_minutes": 15,
            "max_visit_minutes": 45,
        },
    }

    def __init__(self) -> None:
        self.walk_speed_kmh = settings.WALK_SPEED_KMH
        self._matrix_concurrency = max(1, settings.DIST_MATRIX_CONCURRENCY)

    async def initialize(self) -> None:

        await twogis_client.connect_redis()
        await transit_advisor.connect_redis()
        logger.info("✓ Route Planner Service initialised (Redis connected)")

    def _get_intensity_profile(self, intensity: str) -> Dict[str, float]:
        return self.INTENSITY_PROFILES.get(intensity, self.INTENSITY_PROFILES["medium"])

    def _effective_visit_minutes(self, base_minutes: float, intensity: str) -> float:
        minutes = base_minutes or 0.0
        if minutes <= 0:
            minutes = 30.0
        profile = self._get_intensity_profile(intensity)
        adjusted = minutes * profile["visit_duration_multiplier"]
        min_minutes = profile["min_visit_minutes"]
        max_minutes = profile["max_visit_minutes"]
        return float(max(min_minutes, min(max_minutes, max(5.0, adjusted))))

    async def OptimizeRoute(
        self,
        request: route_pb2.RouteOptimizationRequest,
        context,
    ) -> route_pb2.RouteOptimizationResponse:
        try:
            pois = list(request.pois)
            if not pois:
                return route_pb2.RouteOptimizationResponse()

            start_point: CoordinateTuple = (request.start_lat, request.start_lon)
            available_minutes = request.available_hours * 60
            intensity = (request.intensity or "medium").lower()

            filtered_pois = self._filter_dense_pois(pois, intensity)
            if len(filtered_pois) < len(pois):
                logger.info(
                    "Filtered dense cluster of POIs: %s → %s",
                    len(pois),
                    len(filtered_pois),
                )
            pois = filtered_pois

            matrix = await self._build_distance_matrix(start_point, pois)
            if matrix is None:
                matrix = self._fallback_distance_matrix(start_point, pois)

            route_indices, _, _ = self._nearest_neighbor_route(
                matrix=matrix,
                pois=pois,
                available_minutes=available_minutes,
                intensity=intensity,
            )

            if not route_indices:
                return route_pb2.RouteOptimizationResponse()

            ordered_route = [pois[idx] for idx in route_indices]
            legs, totals = await self._build_route_legs(
                start_point, ordered_route, intensity
            )

            logger.info(
                "✓ Optimised route (%s): %s POIs, %.2f km, %.0f min",
                intensity,
                len(ordered_route),
                totals["total_distance"],
                totals["total_duration"],
            )

            return route_pb2.RouteOptimizationResponse(
                optimized_route=ordered_route,
                total_distance_km=totals["total_distance"],
                total_minutes=int(round(totals["total_duration"])),
                legs=legs,
                total_walking_distance_km=totals["walking_distance"],
                total_transit_distance_km=totals["transit_distance"],
            )

        except Exception as exc:
            logger.exception("Route optimization failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Route optimization failed: {exc}")
            return route_pb2.RouteOptimizationResponse()

    async def CalculateRouteGeometry(
        self,
        request: route_pb2.RouteGeometryRequest,
        context,
    ) -> route_pb2.RouteGeometryResponse:
        try:
            points: List[CoordinateTuple] = [
                (request.start_lat, request.start_lon)
            ] + [
                (wp.lat, wp.lon) for wp in request.waypoints
            ]

            if len(points) < 2:
                return route_pb2.RouteGeometryResponse(
                    geometry=[
                        route_pb2.Coordinate(lat=lat, lon=lon) for lat, lon in points
                    ],
                    total_distance_km=0.0,
                )

            geometry_points = await self._build_geometry(points)
            if not geometry_points:
                geometry_points = points

            total_distance = self._geometry_distance(geometry_points)

            return route_pb2.RouteGeometryResponse(
                geometry=[
                    route_pb2.Coordinate(lat=lat, lon=lon)
                    for lat, lon in geometry_points
                ],
                total_distance_km=total_distance,
            )

        except Exception as exc:
            logger.exception("Geometry calculation failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Geometry calculation failed: {exc}")
            return route_pb2.RouteGeometryResponse()

    def _filter_dense_pois(
        self,
        pois: Sequence[route_pb2.POIInfo],
        intensity: str,
    ) -> List[route_pb2.POIInfo]:
        if len(pois) <= 1:
            return list(pois)

        base_threshold = self.CLUSTER_DISTANCE_BY_INTENSITY.get(
            intensity,
            self.CLUSTER_DISTANCE_BY_INTENSITY["medium"],
        )
        thresholds = [
            base_threshold,
            max(base_threshold * 0.75, 0.2),
            max(base_threshold * 0.5, 0.14),
            0.1,
        ]

        deduped_thresholds: List[float] = []
        for value in thresholds:
            value = round(value, 6)
            if value <= 0:
                continue
            if not deduped_thresholds or value < deduped_thresholds[-1]:
                deduped_thresholds.append(value)

        thresholds = deduped_thresholds

        selected: List[route_pb2.POIInfo] = []
        selected_ids = set()

        for threshold in thresholds:
            for poi in pois:
                if poi.id in selected_ids:
                    continue

                if self._is_far_enough(poi, selected, threshold):
                    selected.append(poi)
                    selected_ids.add(poi.id)

                    if len(selected) >= len(pois):
                        break

            if len(selected) >= len(pois):
                break

        return selected if selected else list(pois)

    def _is_far_enough(
        self,
        poi: route_pb2.POIInfo,
        selected: Sequence[route_pb2.POIInfo],
        min_distance_km: float,
    ) -> bool:
        if min_distance_km <= 0.0 or not selected:
            return True

        for existing in selected:
            distance = geodesic(
                (poi.lat, poi.lon),
                (existing.lat, existing.lon),
            ).km
            if distance < min_distance_km:
                return False

        return True

    async def _build_distance_matrix(
        self, start_point: CoordinateTuple, pois: Sequence[route_pb2.POIInfo]
    ) -> Optional[np.ndarray]:
        all_points = [start_point] + [(poi.lat, poi.lon) for poi in pois]

        max_points = 10

        if len(all_points) <= max_points:
            try:
                data = await twogis_client.get_distance_matrix(
                    sources=all_points, targets=all_points, transport="pedestrian"
                )
                if not data:
                    return None

                matrix = twogis_client.parse_distance_matrix(
                    data, num_sources=len(all_points), num_targets=len(all_points)
                )
                return np.array(matrix)
            except Exception as exc:
                logger.warning(
                    "Distance matrix unavailable, fallback to haversine: %s", exc
                )
                return None

        logger.info(
            "Computing distance matrix in batches: %s points (concurrency=%s)",
            len(all_points),
            self._matrix_concurrency,
        )

        n = len(all_points)
        matrix = np.full((n, n), float("inf"))
        chunk_size = max(2, max_points // 2)
        semaphore = asyncio.Semaphore(self._matrix_concurrency)
        tasks: List[asyncio.Task] = []

        async def fetch_block(
            src_indices: List[int],
            tgt_indices: List[int],
            block_points: List[CoordinateTuple],
            block_sources: List[int],
            block_targets: List[int],
        ) -> Tuple[List[int], List[int], List[List[float]]]:
            async with semaphore:
                try:
                    data = await twogis_client.request_distance_matrix(
                        block_points,
                        block_sources,
                        block_targets,
                        transport="pedestrian",
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Distance matrix batch failed ({src_indices}→{tgt_indices}): {exc}"
                    ) from exc

            if not data:
                raise RuntimeError(
                    f"Empty distance matrix batch ({src_indices}→{tgt_indices})"
                )

            block_matrix = twogis_client.parse_distance_matrix(
                data,
                num_sources=len(block_sources),
                num_targets=len(block_targets),
            )

            normalized: List[List[float]] = []
            for s_offset, s_idx in enumerate(src_indices):
                row: List[float] = []
                for t_offset, t_idx in enumerate(tgt_indices):
                    value = block_matrix[s_offset][t_offset]
                    if not np.isfinite(value):
                        value = geodesic(all_points[s_idx], all_points[t_idx]).km
                    row.append(value)
                normalized.append(row)

            return src_indices, tgt_indices, normalized

        for src_start in range(0, n, chunk_size):
            src_indices = list(range(src_start, min(n, src_start + chunk_size)))

            for tgt_start in range(0, n, chunk_size):
                tgt_indices = list(range(tgt_start, min(n, tgt_start + chunk_size)))

                union: List[int] = []
                local_index: Dict[int, int] = {}

                for idx in src_indices + tgt_indices:
                    if idx not in local_index:
                        local_index[idx] = len(union)
                        union.append(idx)

                block_points = [all_points[idx] for idx in union]
                block_sources = [local_index[idx] for idx in src_indices]
                block_targets = [local_index[idx] for idx in tgt_indices]

                tasks.append(
                    asyncio.create_task(
                        fetch_block(
                            src_indices,
                            tgt_indices,
                            block_points,
                            block_sources,
                            block_targets,
                        )
                    )
                )

        if not tasks:
            return None

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Distance matrix batch failed: %s", result)
                return None

            src_indices, tgt_indices, block_values = result
            for s_offset, s_idx in enumerate(src_indices):
                for t_offset, t_idx in enumerate(tgt_indices):
                    matrix[s_idx][t_idx] = block_values[s_offset][t_offset]

        for i in range(n):
            matrix[i][i] = 0.0

        return matrix

    def _fallback_distance_matrix(
        self, start_point: CoordinateTuple, pois: Sequence[route_pb2.POIInfo]
    ) -> np.ndarray:
        n = len(pois) + 1
        matrix = np.zeros((n, n))
        points = [start_point] + [(poi.lat, poi.lon) for poi in pois]

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                matrix[i][j] = geodesic(points[i], points[j]).km
        return matrix

    def _nearest_neighbor_route(
        self,
        matrix: np.ndarray,
        pois: Sequence[route_pb2.POIInfo],
        available_minutes: float,
        intensity: str,
    ) -> Tuple[List[int], float, float]:
        route: List[int] = []
        remaining = set(range(len(pois)))
        current_idx = -1
        total_time = 0.0
        total_distance = 0.0

        while remaining:
            best_idx: Optional[int] = None
            best_score = float("inf")

            for poi_idx in remaining:
                dist = matrix[current_idx + 1][poi_idx + 1]
                walk_time = self._calculate_walk_time_minutes(dist, intensity)
                poi_time = self._effective_visit_minutes(
                    pois[poi_idx].avg_visit_minutes, intensity
                )

                candidate_time = total_time + walk_time + poi_time
                if candidate_time > available_minutes:
                    continue

                if dist < best_score:
                    best_score = dist
                    best_idx = poi_idx

            if best_idx is None:
                break

            distance = matrix[current_idx + 1][best_idx + 1]
            total_distance += distance
            total_time += self._calculate_walk_time_minutes(distance, intensity)
            total_time += self._effective_visit_minutes(
                pois[best_idx].avg_visit_minutes, intensity
            )
            route.append(best_idx)
            remaining.remove(best_idx)
            current_idx = best_idx

        return route, total_time, total_distance

    def _calculate_walk_time_minutes(self, distance_km: float, intensity: str) -> float:
        if distance_km <= 0:
            return 0.0
        profile = self._get_intensity_profile(intensity)
        walk_speed = max(0.5, self.walk_speed_kmh * profile["walk_speed_multiplier"])
        return (distance_km / walk_speed) * 60.0

    async def _build_route_legs(
        self,
        start_point: CoordinateTuple,
        ordered_route: Sequence[route_pb2.POIInfo],
        intensity: str,
    ) -> Tuple[List[route_pb2.RouteLeg], Dict[str, float]]:
        legs: List[route_pb2.RouteLeg] = []
        totals = {
            "total_distance": 0.0,
            "total_duration": 0.0,
            "walking_distance": 0.0,
            "transit_distance": 0.0,
        }

        current = start_point
        for poi in ordered_route:
            target = (poi.lat, poi.lon)
            leg, stats = await self._plan_leg(current, target, intensity)
            legs.append(leg)

            totals["total_distance"] += stats["distance"]
            totals["total_duration"] += stats["duration"]
            totals["walking_distance"] += stats.get("walking_distance", 0.0)
            totals["transit_distance"] += stats.get("transit_distance", 0.0)

            current = target

        return legs, totals

    async def _plan_leg(
        self,
        start: CoordinateTuple,
        end: CoordinateTuple,
        intensity: str,
    ) -> Tuple[route_pb2.RouteLeg, Dict[str, float]]:
        walk_route = await twogis_client.get_walking_route([start, end])

        walk_distance = geodesic(start, end).km
        walk_duration = self._calculate_walk_time_minutes(walk_distance, intensity)
        walk_maneuvers: List[Dict[str, float | str]] = []

        if walk_route:
            walk_distance = walk_route.get("distance", 0) / 1000.0
            walk_duration = walk_route.get("duration", 0) / 60.0
            walk_maneuvers = twogis_client.parse_maneuvers(walk_route)

        transit_option = await transit_advisor.suggest_transit(start, end)
        if transit_option:
            transit_duration = float(transit_option.get("duration_min") or 0.0)
            walk_to_board = float(transit_option.get("walk_to_board_m") or 0.0)
            walk_from_alight = float(transit_option.get("walk_from_alight_m") or 0.0)
            access_minutes = self._calculate_walk_time_minutes(
                (walk_to_board + walk_from_alight) / 1000.0,
                intensity,
            )

            effective_transit_duration = transit_duration + access_minutes
            if effective_transit_duration and effective_transit_duration < walk_duration * 0.9:
                leg = self._build_transit_leg(start, end, transit_option, intensity)
                return leg, {
                    "distance": float(
                        transit_option.get("distance_km") or walk_distance
                    ),
                    "duration": effective_transit_duration,
                    "walking_distance": (walk_to_board + walk_from_alight) / 1000.0,
                    "transit_distance": float(
                        transit_option.get("distance_km") or walk_distance
                    ),
                }

        leg = self._build_walking_leg(start, end, walk_distance, walk_duration, walk_maneuvers)
        return leg, {
            "distance": walk_distance,
            "duration": walk_duration,
            "walking_distance": walk_distance,
            "transit_distance": 0.0,
        }

    def _build_walking_leg(
        self,
        start: CoordinateTuple,
        end: CoordinateTuple,
        distance_km: float,
        duration_min: float,
        maneuvers: Sequence[Dict[str, float | str]],
    ) -> route_pb2.RouteLeg:
        leg = route_pb2.RouteLeg(
            start=route_pb2.Coordinate(lat=start[0], lon=start[1]),
            end=route_pb2.Coordinate(lat=end[0], lon=end[1]),
            distance_km=distance_km,
            duration_minutes=duration_min,
            mode="walking",
        )

        for maneuver in maneuvers:
            leg.maneuvers.add(
                instruction=str(maneuver.get("instruction", "")),
                street_name=str(maneuver.get("street_name", "")),
                distance_m=float(maneuver.get("distance_m") or 0.0),
                duration_sec=float(maneuver.get("duration_s") or 0.0),
            )

        return leg

    def _build_transit_leg(
        self,
        start: CoordinateTuple,
        end: CoordinateTuple,
        transit: Dict[str, Any],
        intensity: str,
    ) -> route_pb2.RouteLeg:
        distance_km = float(transit.get("distance_km") or 0.0)
        if distance_km <= 0:
            distance_km = geodesic(start, end).km

        duration_min = float(transit.get("duration_min") or 0.0)
        if duration_min <= 0:
            duration_min = self._calculate_walk_time_minutes(distance_km, intensity)

        leg = route_pb2.RouteLeg(
            start=route_pb2.Coordinate(lat=start[0], lon=start[1]),
            end=route_pb2.Coordinate(lat=end[0], lon=end[1]),
            distance_km=distance_km,
            duration_minutes=duration_min,
            mode="transit",
        )

        for step in transit.get("instructions", []) or []:
            leg.maneuvers.add(
                instruction=str(step.get("instruction", "")),
                street_name="",
                distance_m=float(step.get("distance_m") or 0.0)
                if step.get("distance_m") is not None
                else 0.0,
                duration_sec=float(step.get("duration_s") or 0.0)
                if step.get("duration_s") is not None
                else 0.0,
            )

        details = route_pb2.TransitLegDetails(
            provider=str(transit.get("provider", "")),
            line_name=str(transit.get("line_name", "")),
            vehicle_type=str(transit.get("vehicle_type", "")),
            direction=str(transit.get("direction", "")),
            vehicle_number=str(transit.get("vehicle_number", "")),
            summary=str(transit.get("summary", "")),
            departure_time=str(transit.get("departure_time", "")),
            arrival_time=str(transit.get("arrival_time", "")),
            notes="; ".join(
                note for note in (transit.get("notes") or []) if note
            ),
            walk_to_board_meters=float(transit.get("walk_to_board_m") or 0.0),
            walk_from_alight_meters=float(transit.get("walk_from_alight_m") or 0.0),
        )

        boarding = transit.get("boarding_stop") or {}
        if boarding:
            details.boarding.name = str(boarding.get("name", ""))
            details.boarding.side = str(boarding.get("side", ""))
            if boarding.get("lat") is not None and boarding.get("lon") is not None:
                details.boarding.position.CopyFrom(
                    route_pb2.Coordinate(
                        lat=float(boarding.get("lat")), lon=float(boarding.get("lon"))
                    )
                )

        alighting = transit.get("alighting_stop") or {}
        if alighting:
            details.alighting.name = str(alighting.get("name", ""))
            details.alighting.side = str(alighting.get("side", ""))
            if alighting.get("lat") is not None and alighting.get("lon") is not None:
                details.alighting.position.CopyFrom(
                    route_pb2.Coordinate(
                        lat=float(alighting.get("lat")),
                        lon=float(alighting.get("lon")),
                    )
                )

        leg.transit.CopyFrom(details)
        return leg

    async def _build_geometry(
        self, points: Sequence[CoordinateTuple]
    ) -> List[CoordinateTuple]:
        if len(points) <= 1:
            return list(points)

        if len(points) <= 10:
            route = await twogis_client.get_walking_route(list(points))
            if route:
                geometry = twogis_client.parse_geometry(route)
                if geometry:
                    return geometry

        geometry: List[CoordinateTuple] = []
        chunk_size = 9
        for idx in range(0, len(points) - 1, chunk_size):
            chunk = list(points[idx : idx + chunk_size + 1])
            route = await twogis_client.get_walking_route(chunk)
            if route:
                chunk_geometry = twogis_client.parse_geometry(route)
                if geometry and chunk_geometry:
                    chunk_geometry = chunk_geometry[1:]
                geometry.extend(chunk_geometry or chunk[1:])
            else:
                geometry.extend(chunk[1:])

        return geometry or list(points)

    def _geometry_distance(self, geometry: Sequence[CoordinateTuple]) -> float:
        if len(geometry) < 2:
            return 0.0

        total = 0.0
        for idx in range(len(geometry) - 1):
            total += geodesic(geometry[idx], geometry[idx + 1]).km
        return total


route_planner = RoutePlannerServicer()
