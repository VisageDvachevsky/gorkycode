#!/usr/bin/env python3
"""POI Data Loader – inserts JSON dataset into PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Sequence

import asyncpg

from poi_loader_utils import PoiDataError, load_poi_data, resolve_poi_json_path

DEFAULT_DATABASE_URL = "postgresql://aitourist:dev_password@ai-tourist-postgresql:5432/aitourist_db"


async def load_pois() -> None:
    """Load POI data from JSON file into the database."""

    print("🚀 Starting POI data load...")

    try:
        data_path = resolve_poi_json_path()
        pois = load_poi_data(data_path)
    except PoiDataError as exc:  # pragma: no cover - CLI output
        print(f"❌ {exc}")
        if exc.checked:
            print("   Checked paths:")
            for candidate in exc.checked:
                print(f"     - {candidate}")
        sys.exit(1)

    print(f"📂 Loading POI data from: {data_path}")
    print(f"📊 Found {len(pois)} POIs")

    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    print("🔌 Connecting to database...")
    try:
        conn = await asyncpg.connect(database_url, record_class=None)
    except Exception as exc:  # pragma: no cover - CLI output
        print(f"❌ Database connection failed: {exc}")
        sys.exit(1)

    try:
        await _load_into_database(conn, pois)
    except Exception as exc:  # pragma: no cover - CLI output
        print(f"❌ Error during data load: {exc}")
        sys.exit(1)
    finally:
        await conn.close()


ASYNC_WARNING = "⚠️  Warning: Failed to insert POI '{name}': {error}"


async def _load_into_database(conn: asyncpg.Connection, pois: Sequence[dict]) -> None:
    table_exists = await conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pois')"
    )

    if not table_exists:
        raise RuntimeError("pois table does not exist. Run database migrations first.")

    print("🧹 Clearing existing POI data...")
    await conn.execute("TRUNCATE TABLE pois RESTART IDENTITY CASCADE")

    print("📥 Inserting POIs...")
    inserted = 0

    for poi in pois:
        try:
            await conn.execute(
                """
                INSERT INTO pois (
                    name, lat, lon, category, description, rating,
                    avg_visit_minutes, address, tags, social_mode,
                    intensity_level, photo_tip, local_tip
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                poi.get("name", "Unknown"),
                float(poi.get("lat", 0.0)),
                float(poi.get("lon", 0.0)),
                poi.get("category", "other"),
                poi.get("description", ""),
                float(poi.get("rating", 0.0)),
                int(poi.get("avg_visit_minutes", 30)),
                poi.get("address", ""),
                poi.get("tags", []),
                poi.get("social_mode", "any"),
                poi.get("intensity_level", "medium"),
                poi.get("photo_tip", ""),
                poi.get("local_tip", ""),
            )
            inserted += 1
        except Exception as exc:  # pragma: no cover - CLI output
            print(ASYNC_WARNING.format(name=poi.get("name", "unknown"), error=exc))

    count = await conn.fetchval("SELECT COUNT(*) FROM pois")
    print(f"✅ Successfully loaded {count} POIs (inserted: {inserted})")


if __name__ == "__main__":
    asyncio.run(load_pois())
