import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.router import api_router
from app.core.config import settings
from app.grpc.clients import grpc_clients
from typing import Optional

from ai_tourist_common import (
    HealthState,
    ProbeServer,
    configure_logging,
    ensure_trace_id,
    get_trace_id,
    reset_trace_id,
    set_trace_id,
)
logger = configure_logging("api-gateway")
health_state = HealthState("api-gateway")


probe_server: Optional[ProbeServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    boot_token = set_trace_id("bootstrap")
    health_state.mark_not_ready("initialising")
    logger.info("Starting API Gateway")
    logger.info("Environment: %s", settings.ENVIRONMENT)

    global probe_server
    probe_server = ProbeServer("0.0.0.0", settings.METRICS_PORT, health_state)
    probe_server.start()
    logger.info("✓ Probes listening on :%s", settings.METRICS_PORT)

    try:
        await grpc_clients.connect_all()
    except Exception as exc:
        health_state.mark_unhealthy(str(exc))
        probe_server.stop()
        probe_server = None
        reset_trace_id(boot_token)
        raise

    logger.info("Connected to all gRPC services")
    health_state.mark_ready()
    logger.info("API Gateway ready")

    try:
        yield
    finally:
        health_state.mark_not_ready("shutting down")
        logger.info("Shutting down API Gateway")
        await grpc_clients.close_all()
        logger.info("Cleanup complete")
        if probe_server is not None:
            probe_server.stop()
        probe_server = None
        reset_trace_id(boot_token)


app = FastAPI(
    title="AI-Tourist API Gateway",
    version="2.0.0",
    description="Microservices-based tourist route planning API",
    lifespan=lifespan,
    default_response_class=ORJSONResponse
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = ensure_trace_id(headers=request.headers.items())
    token = set_trace_id(trace_id)
    try:
        response = await call_next(request)
    finally:
        reset_trace_id(token)
    response.headers.setdefault("X-Trace-Id", trace_id)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        "%s %s - status=%s duration=%.3fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(api_router, prefix="/api/v1")


@app.get("/healthz")
async def health_check() -> JSONResponse:
    status_code = status.HTTP_200_OK if health_state.live else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {
        "service": health_state.service,
        "status": "ok" if health_state.live else "error",
    }
    if health_state.message:
        payload["message"] = health_state.message
    return JSONResponse(payload, status_code=status_code, headers={"X-Trace-Id": get_trace_id()})


@app.get("/readyz")
async def readiness_check() -> JSONResponse:
    services_status = await grpc_clients.health_check()
    dependencies_ready = all(services_status.values())
    if dependencies_ready and health_state.live:
        health_state.mark_ready()
    else:
        missing = [name for name, ok in services_status.items() if not ok]
        if missing:
            health_state.mark_not_ready(
                "dependencies unavailable: " + ", ".join(sorted(missing))
            )
    ready = health_state.ready and dependencies_ready
    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {
        "service": health_state.service,
        "ready": ready,
        "dependencies": services_status,
    }
    if not ready and health_state.message:
        payload["message"] = health_state.message
    return JSONResponse(payload, status_code=status_code, headers={"X-Trace-Id": get_trace_id()})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
