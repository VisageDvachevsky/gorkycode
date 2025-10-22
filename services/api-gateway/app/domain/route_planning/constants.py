from __future__ import annotations

from datetime import time as dt_time
from typing import Dict, Sequence, Tuple

INTENSITY_PROFILES: Dict[str, Dict[str, float]] = {
    "relaxed": {
        "target_per_hour": 1.3,
        "default_visit_minutes": 55.0,
        "min_visit_minutes": 40.0,
        "max_visit_minutes": 90.0,
        "transition_padding": 8.0,
        "safety_buffer": 20.0,
    },
    "medium": {
        "target_per_hour": 2.0,
        "default_visit_minutes": 42.0,
        "min_visit_minutes": 30.0,
        "max_visit_minutes": 70.0,
        "transition_padding": 6.0,
        "safety_buffer": 15.0,
    },
    "intense": {
        "target_per_hour": 2.8,
        "default_visit_minutes": 30.0,
        "min_visit_minutes": 20.0,
        "max_visit_minutes": 55.0,
        "transition_padding": 4.0,
        "safety_buffer": 10.0,
    },
    "low": {
        "target_per_hour": 1.3,
        "default_visit_minutes": 55.0,
        "min_visit_minutes": 40.0,
        "max_visit_minutes": 90.0,
        "transition_padding": 8.0,
        "safety_buffer": 20.0,
    },
    "high": {
        "target_per_hour": 2.8,
        "default_visit_minutes": 30.0,
        "min_visit_minutes": 20.0,
        "max_visit_minutes": 55.0,
        "transition_padding": 4.0,
        "safety_buffer": 10.0,
    },
}

INTENSITY_CANDIDATE_MULTIPLIER: Dict[str, float] = {
    "relaxed": 1.5,
    "low": 1.5,
    "medium": 2.0,
    "intense": 2.5,
    "high": 2.5,
}

INTENSITY_SEARCH_RADIUS_KM: Dict[str, float] = {
    "relaxed": 5.0,
    "low": 5.0,
    "medium": 7.5,
    "intense": 10.0,
    "high": 10.0,
}

RECOMMENDED_COFFEE_INTERVAL: Dict[str, int] = {
    "relaxed": 90,
    "low": 90,
    "medium": 90,
    "intense": 100,
    "high": 100,
}

TIME_PHASES: Tuple[Tuple[str, int, int], ...] = (
    ("early_morning", 6, 9),
    ("morning", 9, 12),
    ("lunch", 12, 14),
    ("day", 14, 17),
    ("evening", 17, 19),
    ("night", 19, 22),
)

TIME_PHASE_CATEGORY_PREFS: Dict[str, Dict[str, float]] = {
    "early_morning": {
        "park": 1.0,
        "embankment": 0.95,
        "viewpoint": 0.92,
        "memorial": 0.82,
        "default": 0.75,
    },
    "morning": {
        "museum": 0.95,
        "art_object": 0.88,
        "architecture": 0.86,
        "memorial": 0.84,
        "default": 0.78,
    },
    "lunch": {
        "cafe": 1.0,
        "restaurant": 0.95,
        "market": 0.92,
        "embankment": 0.8,
        "default": 0.74,
    },
    "day": {
        "museum": 0.9,
        "art_object": 0.88,
        "memorial": 0.86,
        "park": 0.82,
        "architecture": 0.85,
        "default": 0.78,
    },
    "evening": {
        "art_object": 0.94,
        "architecture": 0.95,
        "viewpoint": 0.92,
        "embankment": 0.9,
        "memorial": 0.88,
        "default": 0.8,
    },
    "night": {
        "art_object": 0.9,
        "memorial": 0.88,
        "monument": 0.88,
        "embankment": 0.85,
        "park": 0.52,
        "default": 0.72,
    },
    "default": {"default": 0.75},
}

SOCIAL_MODE_CATEGORY_PREFS: Dict[str, Dict[str, float]] = {
    "solo": {
        "museum": 0.95,
        "memorial": 0.9,
        "park": 0.82,
        "art_object": 0.8,
        "default": 0.76,
    },
    "friends": {
        "art_object": 0.96,
        "mosaic": 0.94,
        "decorative_art": 0.92,
        "market": 0.86,
        "default": 0.74,
    },
    "couple": {
        "embankment": 0.95,
        "viewpoint": 0.94,
        "architecture": 0.88,
        "cafe": 0.9,
        "default": 0.78,
    },
    "family": {
        "museum": 0.9,
        "park": 0.9,
        "memorial": 0.85,
        "default": 0.8,
    },
}

INDOOR_CATEGORIES: Tuple[str, ...] = (
    "museum",
    "gallery",
    "church",
    "religious_site",
    "cafe",
    "restaurant",
)

OUTDOOR_CATEGORIES: Tuple[str, ...] = (
    "park",
    "embankment",
    "viewpoint",
    "mosaic",
    "art_object",
    "decorative_art",
    "monument",
    "memorial",
)

STREET_ART_HINTS: Sequence[str] = (
    "стрит",
    "street",
    "граффити",
    "мурал",
)

HISTORY_HINTS: Sequence[str] = (
    "истор",
    "history",
    "кремл",
    "усадьб",
)

MORNING_AVOID_KEYWORDS: Sequence[str] = (
    "кофе",
    "coffee",
    "кафе",
    "бар",
    "brunch",
)

NIGHT_UNSAFE_KEYWORDS: Sequence[str] = (
    "сквер",
    "тропа",
    "двор",
    "аллея",
    "парк",
)

NIGHT_PREFERRED_KEYWORDS: Sequence[str] = (
    "набереж",
    "кремл",
    "центр",
    "площад",
)

CATEGORY_STREET_ART: Sequence[str] = (
    "art_object",
    "mosaic",
    "decorative_art",
)

CATEGORY_HISTORY: Sequence[str] = (
    "museum",
    "monument",
    "memorial",
    "architecture",
    "religious_site",
    "sculpture",
)

EMOJI_BY_CATEGORY: Dict[str, str] = {
    "museum": "🏛",
    "monument": "🗿",
    "memorial": "🕯",
    "architecture": "🏰",
    "religious_site": "⛪",
    "sculpture": "🎭",
    "art_object": "🎨",
    "mosaic": "🧩",
    "decorative_art": "🖼",
    "park": "🌳",
}

TYPICAL_OPENING_HOURS: Dict[str, Tuple[dt_time, dt_time]] = {
    "museum": (dt_time(10, 0), dt_time(19, 0)),
    "art_object": (dt_time(9, 0), dt_time(21, 0)),
    "architecture": (dt_time(9, 0), dt_time(22, 0)),
    "religious_site": (dt_time(8, 0), dt_time(20, 0)),
    "park": (dt_time(0, 0), dt_time(23, 59)),
    "memorial": (dt_time(0, 0), dt_time(23, 59)),
    "monument": (dt_time(0, 0), dt_time(23, 59)),
    "viewpoint": (dt_time(9, 0), dt_time(22, 0)),
    "embankment": (dt_time(0, 0), dt_time(23, 59)),
    "cafe": (dt_time(8, 0), dt_time(23, 0)),
    "bar": (dt_time(12, 0), dt_time(2, 0)),
    "sculpture": (dt_time(9, 0), dt_time(22, 0)),
    "default": (dt_time(9, 0), dt_time(21, 0)),
}
