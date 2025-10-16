import json
import asyncio
import asyncpg
import os

async def load_pois():
    poi_file = os.environ.get('POI_FILE', 'data/poi.json')
    
    print(f"Reading {poi_file}...")
    with open(poi_file, 'r', encoding='utf-8') as f:
        pois = json.load(f)
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='aitourist',
        password=os.environ['DB_PASSWORD'],
        database='aitourist_db'
    )
    
    try:
        existing = await conn.fetchval('SELECT COUNT(*) FROM pois')
        print(f"Current POIs in database: {existing}")
        
        if existing > 0:
            print("Clearing existing POIs...")
            await conn.execute('DELETE FROM pois')
        
        loaded = 0
        for i, poi in enumerate(pois, 1):
            try:
                await conn.execute('''
                    INSERT INTO pois (id, name, lat, lon, category, tags, description, 
                                      avg_visit_minutes, rating, social_mode, intensity_level,
                                      local_tip, photo_tip, address)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11, $12, $13, $14)
                ''',
                    poi.get('id', i),
                    poi['name'],
                    poi['lat'],
                    poi['lon'],
                    poi['category'],
                    json.dumps(poi.get('tags', [])),
                    poi.get('description', ''),
                    poi.get('avg_visit_minutes', 30),
                    poi.get('rating', 0.0),
                    poi.get('social_mode', 'any'),
                    poi.get('intensity_level', 'medium'),
                    poi.get('local_tip', ''),
                    poi.get('photo_tip', ''),
                    poi.get('address', '')
                )
                loaded += 1
                if i % 50 == 0:
                    print(f"  Loaded {i}/{len(pois)} POIs...")
            except Exception as e:
                print(f"  Warning: Failed to load POI #{poi.get('id', i)} {poi.get('name', 'unknown')}: {e}")
        
        max_id = await conn.fetchval('SELECT MAX(id) FROM pois')
        if max_id:
            await conn.execute(f"SELECT setval('pois_id_seq', {max_id})")
        
        total = await conn.fetchval('SELECT COUNT(*) FROM pois')
        print(f"✅ Successfully loaded {loaded} POIs")
        print(f"📊 Total POIs in database: {total}")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(load_pois())