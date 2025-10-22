from __future__ import annotations

from typing import Optional, Sequence, Tuple

import httpx


class ElevationService:
    def __init__(self, base_url: Optional[str]) -> None:
        self.base_url = (base_url or "").strip()

    def is_enabled(self) -> bool:
        return bool(self.base_url)

    async def lookup_profile(self, coordinates: Sequence[Tuple[float, float]]) -> Optional[Sequence[float]]:
        if not self.is_enabled() or not coordinates:
            return None
        url = self.base_url.rstrip("/")
        coords = list(coordinates)
        payload = {
            "locations": [
                {"latitude": float(lat), "longitude": float(lon)} for lat, lon in coords
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except Exception:
            return None
        data = response.json()
        results = data.get("results")
        if not results:
            return None
        elevations = [float(item.get("elevation", 0.0)) for item in results]
        return elevations

    async def elevation_delta(self, start: Tuple[float, float], end: Tuple[float, float]) -> Optional[float]:
        profile = await self.lookup_profile((start, end))
        if not profile or len(profile) < 2:
            return None
        return profile[-1] - profile[0]
