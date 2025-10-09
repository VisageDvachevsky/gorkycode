import asyncio
import json
from pathlib import Path
from sqlalchemy import select
from app.core.database import async_session_maker, init_db
from app.models.poi import POI
from app.services.embedding import embedding_service


async def load_pois():
    await init_db()
    await embedding_service.connect_redis()
    
    data_path = Path(__file__).parent.parent.parent / "data" / "poi.json"
    
    with open(data_path, "r", encoding="utf-8") as f:
        pois_data = json.load(f)
    
    async with async_session_maker() as session:
        result = await session.execute(select(POI))
        existing_pois = {poi.id: poi for poi in result.scalars().all()}
        
        for poi_data in pois_data:
            poi_id = poi_data["id"]
            
            embedding_text = f"{poi_data['name']} {poi_data['description']} {' '.join(poi_data['tags'])}"
            embedding = embedding_service.generate_embedding(embedding_text)
            
            if poi_id in existing_pois:
                poi = existing_pois[poi_id]
                for key, value in poi_data.items():
                    if key != "id":
                        setattr(poi, key, value)
                poi.embedding = embedding
                print(f"Updated POI: {poi.name}")
            else:
                poi = POI(**poi_data, embedding=embedding)
                session.add(poi)
                print(f"Added POI: {poi.name}")
        
        await session.commit()
        print(f"\nLoaded {len(pois_data)} POIs successfully")


if __name__ == "__main__":
    asyncio.run(load_pois())