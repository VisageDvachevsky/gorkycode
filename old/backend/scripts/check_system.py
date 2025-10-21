import asyncio
import sys
from sqlalchemy import select, func
from app.core.database import async_session_maker, init_db
from app.models.poi import POI
from app.services.embedding import embedding_service
from app.core.config import settings


async def check_system():
    print("🔍 AI-Tourist System Check\n")
    print("=" * 50)
    
    print("\n📊 Configuration:")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  LLM Model: {settings.LLM_MODEL}")
    print(f"  Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"  Database: {settings.DATABASE_URL}")
    
    try:
        await init_db()
        print("\n✅ Database connection: OK")
    except Exception as e:
        print(f"\n❌ Database connection: FAILED - {e}")
        sys.exit(1)
    
    try:
        await embedding_service.connect_redis()
        print("✅ Redis connection: OK")
    except Exception as e:
        print(f"❌ Redis connection: FAILED - {e}")
        sys.exit(1)
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(func.count(POI.id)))
            poi_count = result.scalar()
            print(f"✅ POI Database: {poi_count} points loaded")
            
            if poi_count == 0:
                print("\n⚠️  Warning: No POIs in database!")
                print("   Run: docker compose exec backend poetry run python scripts/load_pois.py")
    except Exception as e:
        print(f"❌ POI check: FAILED - {e}")
    
    try:
        test_embedding = embedding_service.generate_embedding("test")
        print(f"✅ Embedding service: OK (dim={len(test_embedding)})")
    except Exception as e:
        print(f"❌ Embedding service: FAILED - {e}")
        sys.exit(1)
    
    if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
        print("\n⚠️  Warning: No LLM API key configured!")
        print("   Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
    else:
        print("✅ LLM API key: Configured")
    
    print("\n" + "=" * 50)
    print("✅ System check completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(check_system())