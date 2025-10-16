import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import time

from app.api.router import api_router
from app.core.config import settings
from app.grpc.clients import grpc_clients

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting API Gateway...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    await grpc_clients.connect_all()
    logger.info("✓ Connected to all gRPC services")
    
    logger.info("✅ API Gateway ready!")
    
    yield
    
    logger.info("Shutting down API Gateway...")
    await grpc_clients.close_all()
    logger.info("✅ Cleanup complete")


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
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for K8s probes"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "2.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifies gRPC connections"""
    services_status = await grpc_clients.health_check()
    
    all_healthy = all(services_status.values())
    
    return {
        "ready": all_healthy,
        "services": services_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )