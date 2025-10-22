from __future__ import annotations

from typing import Iterable, Sequence

from .constants import CATEGORY_HISTORY, CATEGORY_STREET_ART, HISTORY_HINTS, STREET_ART_HINTS
from .models import POIMetadata


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def contains_keywords(
    items: Sequence[str],
    keywords: Sequence[str],
    *,
    pre_normalized: bool = False,
) -> bool:
    if not items or not keywords:
        return False
    pool = items if pre_normalized else tuple(normalize(item) for item in items if item)
    return any(keyword in token for token in pool for keyword in keywords)


def build_metadata(poi) -> POIMetadata:
    raw_tags = getattr(poi, "tags", []) or []
    normalized_tags = tuple(normalize(tag) for tag in raw_tags if tag)
    normalized_name = normalize(getattr(poi, "name", ""))
    keywords = tuple(value for value in (normalized_name, *normalized_tags) if value)
    category = normalize(getattr(poi, "category", ""))
    return POIMetadata(keywords=keywords, category=category, tags=normalized_tags)


def is_street_art(meta: POIMetadata) -> bool:
    if meta.category in CATEGORY_STREET_ART:
        return True
    return contains_keywords(meta.keywords, STREET_ART_HINTS, pre_normalized=True)


def is_history(meta: POIMetadata) -> bool:
    if meta.category in CATEGORY_HISTORY:
        return True
    return contains_keywords(meta.keywords, HISTORY_HINTS, pre_normalized=True)
