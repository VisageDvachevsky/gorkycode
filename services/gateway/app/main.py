from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.grpc_clients import ml_client, llm_client, routing_client, geocoding_client
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting API Gateway v{settings.VERSION}")
    
    await init_db()
    logger.info("✓ Database initialized")
    
    await ml_client.connect()
    await llm_client.connect()
    await routing_client.connect()
    await geocoding_client.connect()
    logger.info("✓ gRPC clients connected")
    
    health_checks = {
        "ml": await ml_client.health_check(),
        "llm": await llm_client.health_check(),
        "routing": await routing_client.health_check(),
        "geocoding": await geocoding_client.health_check(),
    }
    
    for service, healthy in health_checks.items():
        status = "✓" if healthy else "✗"
        logger.info(f"{status} {service.upper()} service: {'healthy' if healthy else 'unhealthy'}")
    
    if not all(health_checks.values()):
        logger.warning("⚠ Some services unhealthy, but continuing startup")
    
    logger.info("✅ API Gateway ready")
    
    yield
    
    logger.info("🛑 Shutting down API Gateway")
    await ml_client.close()
    await llm_client.close()
    await routing_client.close()
    await geocoding_client.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.2f}"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"➡️  {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"⬅️  {request.method} {request.url.path} - {response.status_code}")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    services = {
        "ml": await ml_client.health_check(),
        "llm": await llm_client.health_check(),
        "routing": await routing_client.health_check(),
        "geocoding": await geocoding_client.health_check(),
    }
    
    all_healthy = all(services.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.VERSION,
        "services": services,
    }


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }