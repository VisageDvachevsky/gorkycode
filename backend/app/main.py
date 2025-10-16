import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import time

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.services.embedding import embedding_service
from app.services.twogis_client import twogis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting AI-Tourist API v0.2.0...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    
    await init_db()
    logger.info("Database initialized")
    
    await embedding_service.connect_redis()
    await twogis_client.connect_redis()
    logger.info("Redis connections established")
    
    if not settings.TWOGIS_API_KEY:
        logger.error("❌ TWOGIS_API_KEY not configured!")
        logger.error("Get your free 2GIS API key at https://dev.2gis.com")
        logger.error("This is REQUIRED for geocoding, routing, and place search")
    else:
        logger.info("✓ 2GIS API key configured")
    
    if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
        logger.warning("⚠ No LLM API key configured! AI explanations will not work.")
    else:
        logger.info("✓ LLM API key configured")
    
    logger.info("AI-Tourist API ready!")
    logger.info("Using 2GIS APIs for:")
    logger.info("  - Geocoding (address → coordinates)")
    logger.info("  - Routing (real walking paths)")
    logger.info("  - Public Transit (bus/tram suggestions)")
    logger.info("  - Places Search (smart cafe discovery)")
    
    yield
    
    logger.info("Shutting down AI-Tourist API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    logger.info(f"➡️  {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"⬅️  {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}s"
    )
    
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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "2gis": bool(settings.TWOGIS_API_KEY),
            "llm": bool(settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI-Tourist API v0.2.0",
        "version": settings.VERSION,
        "powered_by": "2GIS APIs",
        "docs": "/docs"
    }