"""Centralised logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from .tracing import get_trace_id


class TraceIdFilter(logging.Filter):
    """Injects the current trace identifier into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - inherited
        record.trace_id = get_trace_id()
        return True


def configure_logging(service_name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure root logging with trace correlation."""

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | trace_id=%(trace_id)s | %(message)s"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(TraceIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    return logging.getLogger(service_name)


def bind_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience helper to obtain a configured logger."""

    return logging.getLogger(name)
