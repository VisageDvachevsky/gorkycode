from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Iterable, Optional
from uuid import uuid4

TRACE_HEADER_CANDIDATES: tuple[str, ...] = (
    "x-trace-id",
    "x-request-id",
    "traceparent",
    "x-b3-traceid",
)

_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="-")
_TRACE_ID_PATTERN = re.compile(r"^[a-fA-F0-9-]{8,64}$")


def _normalise(value: str) -> str:
    value = value.strip()
    if _TRACE_ID_PATTERN.match(value):
        return value.lower()
    return uuid4().hex


def ensure_trace_id(value: Optional[str] = None, *, headers: Optional[Iterable[tuple[str, str]]] = None) -> str:
    """Resolve or generate a trace identifier.

    Args:
        value: Explicit trace id candidate.
        headers: Optional iterable of key/value metadata pairs.

    Returns:
        A valid trace identifier.
    """

    if value:
        return _normalise(value)

    if headers:
        for key, header_value in headers:
            if key.lower() in TRACE_HEADER_CANDIDATES and header_value:
                return _normalise(header_value)

    return uuid4().hex


def set_trace_id(trace_id: str):  # noqa: ANN001 - ContextVar API
    return _TRACE_ID.set(_normalise(trace_id))


def reset_trace_id(token):  # noqa: ANN001 - ContextVar API
    if token is not None:
        _TRACE_ID.reset(token)


def get_trace_id() -> str:
    return _TRACE_ID.get()
