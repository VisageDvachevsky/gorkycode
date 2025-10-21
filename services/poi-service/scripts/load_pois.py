from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Sequence

# Ensure shared scripts are importable before loading helper utilities.
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
SERVICE_ROOT = SCRIPT_DIR.parent
try:
    REPO_ROOT_HINT = SERVICE_ROOT.parents[1]
except IndexError:
    REPO_ROOT_HINT = SERVICE_ROOT

_CANDIDATE_SCRIPT_DIRS = [
    SCRIPT_DIR,
    *(ancestor / "scripts" for ancestor in SCRIPT_PATH.parents),
]
for _candidate in _CANDIDATE_SCRIPT_DIRS:
    if _candidate.is_dir():
        _candidate_str = str(_candidate)
        if _candidate_str not in sys.path:
            sys.path.insert(0, _candidate_str)

from poi_loader_utils import (
    PoiDataError,
    ensure_project_root,
    ensure_pythonpath,
    load_poi_data,
    resolve_poi_json_path,
)

from sqlalchemy import Column, Float, Integer, String, Text, Time, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

PROJECT_ROOT = ensure_project_root(REPO_ROOT_HINT, SERVICE_ROOT)
ensure_pythonpath(
    PROJECT_ROOT,
    PROJECT_ROOT / "scripts",
    SCRIPT_DIR,
    SERVICE_ROOT,
    SERVICE_ROOT / "app",
    PROJECT_ROOT / "app",
)

import grpc

from app.proto.embedding_pb2 import BatchEmbeddingRequest
from app.proto.embedding_pb2_grpc import EmbeddingServiceStub


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://gorkycode:gorkycode_pass@localhost:5432/gorkycode"
)

EMBEDDING_SERVICE_ADDR = os.getenv("EMBEDDING_SERVICE_ADDR", "localhost:50051")
EMBEDDING_BATCH_SIZE = max(1, int(os.getenv("EMBEDDING_BATCH_SIZE", "16")))
EMBEDDING_TIMEOUT = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30"))
EMBEDDING_USE_CACHE = os.getenv("EMBEDDING_USE_CACHE", "1").lower() not in {"0", "false", "no"}

Base = declarative_base()


class POI(Base):
    """POI Model - Full schema matching monolith"""
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    address = Column(String(500))
    category = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(String), default=list)
    description = Column(Text, nullable=False)
    description_en = Column(Text)
    photo_tip = Column(Text)
    local_tip = Column(Text)
    avg_visit_minutes = Column(Integer, default=30)
    open_time = Column(Time)
    close_time = Column(Time)
    social_mode = Column(String(50), default="any")
    intensity_level = Column(String(50), default="medium")
    rating = Column(Float, default=0.0)
    embedding = Column(ARRAY(Float))


class EmbeddingClient:
    """Thin async wrapper around the embedding-service gRPC API."""

    def __init__(self, target: str, *, use_cache: bool, timeout: float):
        self._target = target
        self._use_cache = use_cache
        self._timeout = timeout
        self._channel: grpc.aio.Channel | None = None
        self._stub: EmbeddingServiceStub | None = None

    async def connect(self) -> None:
        """Establish the gRPC channel and wait until it is ready."""

        self._channel = grpc.aio.insecure_channel(self._target)
        await self._channel.channel_ready()
        self._stub = EmbeddingServiceStub(self._channel)

    async def close(self) -> None:
        """Close the underlying gRPC channel."""

        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Request embeddings for a batch of texts."""

        if not texts:
            return []

        if self._stub is None:
            raise RuntimeError("Embedding client is not connected")

        request = BatchEmbeddingRequest(texts=list(texts), use_cache=self._use_cache)
        response = await self._stub.BatchEmbedding(request, timeout=self._timeout)
        vectors = [list(vector.vector) for vector in response.vectors]

        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Embedding service returned {len(vectors)} vectors for {len(texts)} texts"
            )

        return vectors


async def _create_embedding_client() -> EmbeddingClient:
    """Instantiate and connect the embedding client."""

    client = EmbeddingClient(
        EMBEDDING_SERVICE_ADDR,
        use_cache=EMBEDDING_USE_CACHE,
        timeout=EMBEDDING_TIMEOUT,
    )
    await client.connect()
    return client


async def init_db(engine):
    """Initialize database schema"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database schema initialized")


async def load_pois():
    """Load POIs from JSON with embeddings"""
    print("🚀 Starting POI data load...")
    
    try:
        data_path = resolve_poi_json_path()
        pois_data = load_poi_data(data_path)
    except PoiDataError as exc:
        print(f"❌ {exc}")
        if exc.checked:
            print("   Checked paths:")
            for candidate in exc.checked:
                print(f"     - {candidate}")
        sys.exit(1)

    print(f"📂 Loading POI data from: {data_path}")
    print(f"Found {len(pois_data)} POIs in JSON")
    
    print(f"🔌 Connecting to embedding service at {EMBEDDING_SERVICE_ADDR} ...")

    try:
        embedding_client = await _create_embedding_client()
    except Exception as exc:  # pragma: no cover - operational safeguard
        print("❌ Failed to connect to embedding service:", exc)
        print("   Ensure the embedding-service deployment is running and accessible.")
        print("   You can override the address via EMBEDDING_SERVICE_ADDR.")
        sys.exit(1)

    print("✓ Embedding service connection established")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    await init_db(engine)
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        result = await session.execute(select(POI))
        existing_pois = {poi.id: poi for poi in result.scalars().all()}
        
        added_count = 0
        updated_count = 0
        
        for batch_start in range(0, len(pois_data), EMBEDDING_BATCH_SIZE):
            batch = pois_data[batch_start: batch_start + EMBEDDING_BATCH_SIZE]
            batch_texts = [
                f"{poi['name']} {poi.get('description', '')} {' '.join(poi.get('tags', []))}"
                for poi in batch
            ]

            try:
                embeddings = await embedding_client.embed_batch(batch_texts)
            except Exception as exc:  # pragma: no cover - operational safeguard
                print("❌ Failed to generate embeddings:", exc)
                print("   Verify embedding-service logs for more details.")
                await embedding_client.close()
                sys.exit(1)

            for poi_data, embedding in zip(batch, embeddings):
                poi_id = poi_data["id"]

                if poi_id in existing_pois:
                    poi = existing_pois[poi_id]
                    for key, value in poi_data.items():
                        if key != "id" and hasattr(poi, key):
                            setattr(poi, key, value)
                    poi.embedding = embedding
                    updated_count += 1
                    print(f"  ✓ Updated: {poi.name}")
                else:
                    poi = POI(**poi_data, embedding=embedding)
                    session.add(poi)
                    added_count += 1
                    print(f"  ✓ Added: {poi.name}")

        await session.commit()
        print(f"\n✅ POI Load Complete!")
        print(f"   Added: {added_count}")
        print(f"   Updated: {updated_count}")
        print(f"   Total: {len(pois_data)}")

    await embedding_client.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_pois())
