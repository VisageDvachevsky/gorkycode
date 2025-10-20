#!/usr/bin/env python3
"""
POI Data Loader
Loads POI data from data/poi.json into PostgreSQL database
"""
import json
import asyncio
import asyncpg
import os
import sys

async def load_pois():
    """Load POI data from JSON file into database"""
    
    # Read POI data
    print("Reading data/poi.json...")
    try:
        with open('./data/poi.json', 'r', encoding='utf-8') as f:
            pois = json.load(f)
    except FileNotFoundError:
        print("❌ Error: data/poi.json not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        sys.exit(1)
    
    print(f"Found {len(pois)} POIs")
    
    # Get database connection string (prefer env for K8s)
    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://aitourist:dev_password@ai-tourist-postgresql:5432/aitourist_db'  # K8s-friendly fallback
    )
    
    # Connect to database
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(database_url, record_class=None)  # Faster, no Record objects
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Check if table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pois')"
        )
        
        if not table_exists:
            print("❌ Error: pois table does not exist. Run database migrations first.")
            sys.exit(1)
        
        # Clear existing data
        print("Clearing existing POI data...")
        await conn.execute('TRUNCATE TABLE pois RESTART IDENTITY CASCADE')
        
        # Insert POIs
        print("Inserting POIs...")
        inserted = 0
        
        for poi in pois:
            try:
                await conn.execute('''
                    INSERT INTO pois (
                        name, lat, lon, category, description, rating,
                        avg_visit_minutes, address, tags, social_mode,
                        intensity_level, photo_tip, local_tip
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ''',
                    poi.get('name', 'Unknown'),
                    float(poi.get('lat', 0.0)),  # Ensure float
                    float(poi.get('lon', 0.0)),  # Ensure float
                    poi.get('category', 'other'),
                    poi.get('description', ''),
                    float(poi.get('rating', 0.0)),  # Ensure float
                    int(poi.get('avg_visit_minutes', 30)),  # Ensure int
                    poi.get('address', ''),
                    poi.get('tags', []),  # List → text[]
                    poi.get('social_mode', 'any'),
                    poi.get('intensity_level', 'medium'),
                    poi.get('photo_tip', ''),
                    poi.get('local_tip', '')
                )
                inserted += 1
            except Exception as e:
                print(f"⚠ Warning: Failed to insert POI '{poi.get('name', 'unknown')}': {e}")
        
        # Verify count
        count = await conn.fetchval('SELECT COUNT(*) FROM pois')
        
        print(f"✅ Successfully loaded {count} POIs (inserted: {inserted})")
        
    except Exception as e:
        print(f"❌ Error during data load: {e}")
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(load_pois())