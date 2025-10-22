from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class WeatherSnapshot:
    """Normalized weather information for planning heuristics."""

    description: Optional[str]
    condition_key: Optional[str]
    temperature_c: Optional[float]
    precipitation_mm: float
    wind_kmph: Optional[float]
    advice: Optional[str]

    @property
    def is_foggy(self) -> bool:
        if not self.condition_key:
            return False
        lowered = self.condition_key.lower()
        return "fog" in lowered or "туман" in lowered

    @property
    def is_precipitation(self) -> bool:
        if self.precipitation_mm >= 0.2:
            return True
        if not self.condition_key:
            return False
        lowered = self.condition_key.lower()
        return any(marker in lowered for marker in ("rain", "snow", "дожд", "снег", "ливень"))


@dataclass
class CandidateScore:
    poi: object
    embedding_match: float
    contextual: float
    popularity: float
    base_score: float
    penalty: float
    final_score: float
    arrival_time: datetime
    distance_km: float
    category: str
    tags: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class POIMetadata:
    keywords: Tuple[str, ...]
    category: str
    tags: Tuple[str, ...]

    def contains_any(self, needles: Sequence[str]) -> bool:
        keyword_string = " ".join(self.keywords)
        lowered = keyword_string.lower()
        return any(token in lowered for token in needles)
