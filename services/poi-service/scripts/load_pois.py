#!/usr/bin/env python3
"""Load POI data from JSON into PostgreSQL for POI Service."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os
from sentence_transformers import SentenceTransformer

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from poi_loader_utils import PoiDataError, load_poi_data, resolve_poi_json_path


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://gorkycode:gorkycode_pass@localhost:5432/gorkycode"
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")


from sqlalchemy import Column, Integer, String, Float, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base

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
    
    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"✓ Loaded {EMBEDDING_MODEL}")
    
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
        
        for poi_data in pois_data:
            poi_id = poi_data["id"]
            
            embedding_text = f"{poi_data['name']} {poi_data['description']} {' '.join(poi_data.get('tags', []))}"
            embedding = model.encode(embedding_text).tolist()
            
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
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_pois())
