import asyncio
from concurrent import futures

import grpc

from ai_tourist_common import HealthState, ProbeServer, TraceIdInterceptor, configure_logging
from app.core.config import settings
from app.proto import route_pb2_grpc
from app.services.route_planner import RoutePlannerServicer

logger = configure_logging("route-planner-service")


async def serve() -> None:
    logger.info("🚀 Starting Route Planner Service...")

    health_state = HealthState("route-planner-service")
    probe = ProbeServer("0.0.0.0", settings.METRICS_PORT, health_state)
    probe.start()
    logger.info("✓ Probes listening on :%s", settings.METRICS_PORT)

    servicer = RoutePlannerServicer()

    try:
        await servicer.initialize()
    except Exception as exc:  # pragma: no cover - defensive startup guard
        health_state.mark_unhealthy(str(exc))
        probe.stop()
        raise

    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
        ],
        interceptors=[TraceIdInterceptor()],
    )

    route_pb2_grpc.add_RoutePlannerServiceServicer_to_server(servicer, server)

    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")

    logger.info("✅ Route Planner Service listening on port %s", settings.GRPC_PORT)

    await server.start()
    health_state.mark_ready()

    try:
        await server.wait_for_termination()
    finally:
        probe.stop()


if __name__ == "__main__":
    asyncio.run(serve())
