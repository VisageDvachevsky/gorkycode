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
from app.services.geocoding import geocoding_service
from app.services.routing import routing_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting AI-Tourist API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Connect Redis for all services
    await embedding_service.connect_redis()
    await geocoding_service.connect_redis()
    await routing_service.connect_redis()
    logger.info("Redis connections established")
    
    # Check API keys
    if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
        logger.warning("No LLM API key configured! AI explanations will not work.")
    
    if not settings.OPENROUTESERVICE_API_KEY:
        logger.warning(
            "OpenRouteService API key not configured. "
            "Using public endpoint with rate limits. "
            "Get your free key at https://openrouteservice.org/dev/#/signup"
        )
    
    logger.info("AI-Tourist API ready!")
    
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
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI-Tourist API",
        "version": settings.VERSION,
        "docs": "/docs"
    }