from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import asyncpg

# ============================================================================
# POI Loader Utilities (merged from poi_loader_utils)
# ============================================================================

class PoiDataError(RuntimeError):
    def __init__(self, message: str, *, path: Path | None = None, checked: Sequence[Path] | None = None):
        super().__init__(message)
        self.path = path
        self.checked: List[Path] = list(checked or [])


def _iter_candidate_paths(additional: Iterable[os.PathLike[str] | str] | None = None) -> Iterable[Path]:
    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent
    cwd = Path.cwd()
    env_candidates: list[Path] = []
    for env_name in ("POI_JSON_PATH", "POI_DATA_PATH"):
        env_value = os.getenv(env_name)
        if env_value:
            env_candidates.append(Path(env_value).expanduser())
    default_candidates = [
        scripts_dir / "poi.json",
        repo_root / "data" / "poi.json",
        cwd / "data" / "poi.json",
        Path("/data/poi.json"),
        Path("/app/data/poi.json"),
    ]
    combined: List[Path] = []
    for sequence in (env_candidates, list(additional or []), default_candidates):
        for candidate in sequence:
            path = Path(candidate)
            if path not in combined:
                combined.append(path)
    return combined


def resolve_poi_json_path(*, preferred_paths: Iterable[os.PathLike[str] | str] | None = None, require_exists: bool = True) -> Path:
    """Return the first existing POI JSON path.
    Args:
        preferred_paths: Optional iterable of extra paths to check before defaults.
        require_exists: If True, raise :class:`PoiDataError` when nothing is found.
    """
    checked: List[Path] = []
    empty_candidate: Path | None = None
    for candidate in _iter_candidate_paths(preferred_paths):
        candidate = candidate.expanduser()
        checked.append(candidate)
        if candidate.is_file():
            if candidate.stat().st_size == 0:
                empty_candidate = candidate
                continue
            return candidate
    if require_exists:
        if empty_candidate is not None:
            raise PoiDataError(f"POI dataset file is empty: {empty_candidate}", path=empty_candidate, checked=checked)
        raise PoiDataError(
            "POI dataset file not found. Checked: " + ", ".join(str(path) for path in checked),
            path=None,
            checked=checked,
        )
    return checked[-1] if checked else Path("data/poi.json")


def load_poi_data(path: os.PathLike[str] | str | None = None) -> list[dict]:
    """Load POI data from JSON ensuring valid structure."""
    resolved_path = Path(path) if path else resolve_poi_json_path()
    if not resolved_path.is_file():
        raise PoiDataError(
            f"POI dataset file does not exist: {resolved_path}",
            path=resolved_path,
        )
    if resolved_path.stat().st_size == 0:
        raise PoiDataError(f"POI dataset file is empty: {resolved_path}", path=resolved_path)
    try:
        with resolved_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise PoiDataError(f"Invalid JSON in {resolved_path}: {exc}", path=resolved_path) from exc
    if not isinstance(data, list):
        raise PoiDataError(
            f"Expected POI dataset to be a list, got {type(data).__name__} in {resolved_path}",
            path=resolved_path,
        )
    return data


# ============================================================================
# Main POI Loading Script
# ============================================================================

DEFAULT_DATABASE_URL = "postgresql://aitourist:dev_password@ai-tourist-postgresql:5432/aitourist_db"


def _normalize_database_url(database_url: str) -> str:
    """Ensure the DSN is compatible with :func:`asyncpg.connect`."""

    if "://" not in database_url:
        return database_url

    scheme, remainder = database_url.split("://", 1)
    if scheme in {"postgresql+asyncpg", "postgres+asyncpg"}:
        return f"postgresql://{remainder}"
    if scheme == "postgres":
        return f"postgresql://{remainder}"
    return database_url


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

    database_url = _normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

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