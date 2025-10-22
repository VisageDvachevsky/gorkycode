"""Category diversity heuristics for route planning."""

from __future__ import annotations

from typing import List, Sequence, TypeVar

T = TypeVar("T")


def _resolve_category(item: T, category_key: str) -> str:
    value = None
    if hasattr(item, category_key):
        value = getattr(item, category_key)
    elif isinstance(item, dict):
        value = item.get(category_key)
    if value is None:
        return "unknown"
    return str(value)


def enforce_category_diversity(
    pois: Sequence[T],
    max_consecutive: int = 2,
    *,
    category_key: str = "category",
) -> List[T]:
    """Reorder POIs to reduce long sequences of identical categories."""

    entries = list(pois)
    if len(entries) <= 1 or max_consecutive <= 0:
        return entries[:]

    pending = entries[:]
    diversified: List[T] = []

    while pending:
        added = False
        for idx, item in enumerate(list(pending)):
            category = _resolve_category(item, category_key)
            streak = 0
            for existing in reversed(diversified):
                if _resolve_category(existing, category_key) == category:
                    streak += 1
                else:
                    break
            if streak >= max_consecutive:
                continue
            diversified.append(item)
            pending.pop(idx)
            added = True
            break

        if not added:
            diversified.append(pending.pop(0))

    return diversified


__all__ = ["enforce_category_diversity"]
