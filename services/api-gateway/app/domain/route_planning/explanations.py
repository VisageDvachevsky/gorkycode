from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.models.schemas import RouteRequest

from .constants import EMOJI_BY_CATEGORY, HISTORY_HINTS, STREET_ART_HINTS
from .metadata import contains_keywords, normalize


def map_intensity_for_ranking(intensity: str) -> str:
    mapping = {
        "relaxed": "low",
        "low": "low",
        "intense": "high",
        "high": "high",
    }
    return mapping.get(intensity, "medium")


def map_intensity_for_llm(intensity: str) -> str:
    mapping = {
        "low": "relaxed",
        "relaxed": "relaxed",
        "high": "intense",
        "intense": "intense",
    }
    return mapping.get(intensity, intensity)


def build_profile_text(request: RouteRequest) -> str:
    parts: List[str] = []
    if request.interests:
        parts.append(f"Интересы: {request.interests}")
    if request.categories:
        parts.append("Категории: " + ", ".join(request.categories))
    parts.append(f"Формат прогулки: {request.social_mode}")
    parts.append(f"Интенсивность: {request.intensity}")
    parts.append(f"Длительность: {request.hours:.1f} часа")
    return ". ".join(parts)


def fallback_summary(poi_names: List[str]) -> str:
    if not poi_names:
        return "Не удалось сформировать описание маршрута."
    joined = ", ".join(poi_names)
    return f"Предлагаем прогулку по Нижнему Новгороду через точки: {joined}."


CATEGORY_REASON_LABELS: Dict[str, str] = {
    "museum": "музей с сильной экспозицией",
    "memorial": "место памяти и истории",
    "monument": "знаковая городская скульптура",
    "art_object": "яркий арт-объект",
    "mosaic": "редкая мозаика",
    "decorative_art": "необычная инсталляция",
    "park": "спокойный городской парк",
    "embankment": "видовая набережная",
    "viewpoint": "место с красивым видом",
    "architecture": "выразительный архитектурный объект",
}

SOCIAL_MODE_REASON_HINTS: Dict[str, str] = {
    "solo": "подходит для спокойного созерцания",
    "friends": "можно разделить эмоции с друзьями",
    "couple": "создаёт тёплую атмосферу для двоих",
    "family": "комфортно всей семье",
}

PHASE_REASON_HINTS: Dict[str, str] = {
    "early_morning": "мягкий старт утра",
    "morning": "идеально для утреннего визита",
    "lunch": "как раз к обеденной паузе",
    "day": "центр дневной программы",
    "evening": "уютно завершает закатную часть",
    "night": "безопасное место на вечер",
}


def fallback_why(
    name: str,
    description: Optional[str],
    *,
    category: Optional[str],
    social_mode: str,
    phase: Optional[str],
    contextual_score: Optional[float],
) -> str:
    normalized_category = normalize(category)
    category_label = CATEGORY_REASON_LABELS.get(normalized_category)
    phase_label = PHASE_REASON_HINTS.get(phase or "")
    social_label = SOCIAL_MODE_REASON_HINTS.get(social_mode, "")

    highlights = [label for label in (phase_label, category_label, social_label) if label]

    if contextual_score is not None and contextual_score >= 85:
        highlights.append("максимум совпадает с вашим профилем")
    elif contextual_score is not None and contextual_score >= 70:
        highlights.append("отлично ложится в ваши интересы")

    base_description = description.strip() if description else "Уникальная точка маршрута."
    reason = ". ".join(highlights[:2]) if highlights else base_description
    if not reason:
        reason = base_description

    return f"{name}: {reason}. {base_description}"


def emoji_for_poi(category: Optional[str], tags: Iterable[str], fallback: str = "📍") -> str:
    category_key = normalize(category)
    if category_key in EMOJI_BY_CATEGORY:
        return EMOJI_BY_CATEGORY[category_key]
    normalized_tags = [normalize(tag) for tag in tags if tag]
    if contains_keywords(normalized_tags, STREET_ART_HINTS, pre_normalized=True):
        return "🎨"
    if contains_keywords(normalized_tags, HISTORY_HINTS, pre_normalized=True):
        return "🏛"
    return fallback
