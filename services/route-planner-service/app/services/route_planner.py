import logging
from typing import List

import grpc

from app.proto import route_pb2, route_pb2_grpc
from app.services.route_planner_engine import RoutePOI, route_planner_engine
from app.services.routing import routing_service
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class RoutePlannerServicer(route_pb2_grpc.RoutePlannerServiceServicer):
    def __init__(self) -> None:
        self.engine = route_planner_engine
        self.routing = routing_service

    async def initialize(self) -> None:
        await twogis_client.connect_redis()
        logger.info("✓ Route Planner Service initialized")

    async def OptimizeRoute(
        self,
        request: route_pb2.RouteOptimizationRequest,
        context,
    ) -> route_pb2.RouteOptimizationResponse:
        try:
            pois = [self._from_proto(poi) for poi in request.pois]

            if not pois:
                return route_pb2.RouteOptimizationResponse(
                    optimized_route=[],
                    total_distance_km=0.0,
                    total_minutes=0,
                )

            ordered_route, total_distance = await self.engine.optimize_route(
                request.start_lat,
                request.start_lon,
                pois,
                request.available_hours,
            )

            optimized_proto = [self._to_proto(poi) for poi in ordered_route]

            total_minutes = self._calculate_total_minutes(
                request.start_lat,
                request.start_lon,
                ordered_route,
            )

            return route_pb2.RouteOptimizationResponse(
                optimized_route=optimized_proto,
                total_distance_km=total_distance,
                total_minutes=int(total_minutes),
            )
        except Exception as exc:  # pragma: no cover - defensive logging
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
            waypoints = [(wp.lat, wp.lon) for wp in request.waypoints]
            geometry = await self.routing.calculate_route_geometry(
                (request.start_lat, request.start_lon),
                waypoints,
            )

            coordinates = [
                route_pb2.Coordinate(lat=lat, lon=lon)
                for lat, lon in geometry
            ]

            total_distance = 0.0
            if waypoints:
                total_distance = await self.routing.get_route_distance(
                    (request.start_lat, request.start_lon),
                    waypoints,
                )

            return route_pb2.RouteGeometryResponse(
                geometry=coordinates,
                total_distance_km=total_distance,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Geometry calculation failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Geometry calculation failed: {exc}")
            return route_pb2.RouteGeometryResponse()

    def _from_proto(self, poi: route_pb2.POIInfo) -> RoutePOI:
        return RoutePOI(
            id=poi.id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            avg_visit_minutes=poi.avg_visit_minutes or 45,
            rating=poi.rating,
        )

    def _to_proto(self, poi: RoutePOI) -> route_pb2.POIInfo:
        return route_pb2.POIInfo(
            id=poi.id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            avg_visit_minutes=poi.avg_visit_minutes,
            rating=poi.rating,
        )

    def _calculate_total_minutes(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[RoutePOI],
    ) -> int:
        if not pois:
            return 0

        total = 0
        prev_lat, prev_lon = start_lat, start_lon
        for poi in pois:
            dist = self.routing.calculate_distance_km(
                prev_lat,
                prev_lon,
                poi.lat,
                poi.lon,
            )
            total += self.engine.calculate_walk_time_minutes(dist)
            total += poi.avg_visit_minutes
            prev_lat, prev_lon = poi.lat, poi.lon

        return total
