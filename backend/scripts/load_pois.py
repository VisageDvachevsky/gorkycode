import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from app.core.database import async_session_maker, init_db
from app.models.poi import POI
from app.services.embedding import embedding_service

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from poi_loader_utils import PoiDataError, load_poi_data, resolve_poi_json_path


async def load_pois():
    await init_db()
    await embedding_service.connect_redis()
    
    try:
        data_path = resolve_poi_json_path()
        pois_data = load_poi_data(data_path)
    except PoiDataError as exc:
        print(f"❌ {exc}")
        if exc.checked:
            print("   Checked paths:")
            for candidate in exc.checked:
                print(f"     - {candidate}")
        return

    print(f"📂 Loading POI data from: {data_path}")
    
    async with async_session_maker() as session:
        result = await session.execute(select(POI))
        existing_pois = {poi.id: poi for poi in result.scalars().all()}
        
        for poi_data in pois_data:
            poi_id = poi_data["id"]
            
            # Создаём текст для эмбеддинга
            embedding_text = f"{poi_data['name']} {poi_data['description']} {' '.join(poi_data.get('tags', []))}"
            embedding = embedding_service.generate_embedding(embedding_text)
            
            if poi_id in existing_pois:
                poi = existing_pois[poi_id]
                for key, value in poi_data.items():
                    if key != "id":
                        setattr(poi, key, value)
                poi.embedding = embedding
                print(f"✓ Updated POI: {poi.name}")
            else:
                poi = POI(**poi_data, embedding=embedding)
                session.add(poi)
                print(f"✓ Added POI: {poi.name}")
        
        await session.commit()
        print(f"\n✅ Loaded {len(pois_data)} POIs successfully")


if __name__ == "__main__":
    asyncio.run(load_pois())
