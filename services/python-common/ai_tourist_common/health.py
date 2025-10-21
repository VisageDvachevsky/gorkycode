from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest


@dataclass
class HealthState:
    service: str
    started_at: float = field(default_factory=time.monotonic)
    ready: bool = False
    live: bool = True
    message: Optional[str] = None

    def mark_ready(self) -> None:
        self.ready = True
        self.message = None

    def mark_not_ready(self, message: Optional[str] = None) -> None:
        self.ready = False
        self.message = message

    def mark_unhealthy(self, message: Optional[str] = None) -> None:
        self.live = False
        self.message = message


class _ProbeRequestHandler(BaseHTTPRequestHandler):
    state: HealthState

    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - framework method name
        if self.path == "/healthz":
            self._handle_health()
            return
        if self.path == "/readyz":
            self._handle_ready()
            return
        if self.path == "/metrics":
            self._handle_metrics()
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - signature defined by BaseHTTPRequestHandler
        # Suppress default stdout logging to keep service logs clean.
        return

    def _handle_health(self) -> None:
        status = 200 if self.state.live else 503
        payload = {
            "service": self.state.service,
            "status": "ok" if self.state.live else "error",
            "uptime_seconds": round(time.monotonic() - self.state.started_at, 2),
        }
        if self.state.message:
            payload["message"] = self.state.message
        self._write_json(payload, status=status)

    def _handle_ready(self) -> None:
        status = 200 if self.state.ready else 503
        payload = {
            "service": self.state.service,
            "ready": self.state.ready,
        }
        if self.state.message:
            payload["message"] = self.state.message
        self._write_json(payload, status=status)

    def _handle_metrics(self) -> None:
        try:
            output = generate_latest(REGISTRY)
        except Exception as exc:  # pragma: no cover - defensive
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)


class ProbeServer:
    """Simple threaded HTTP server exposing health and metrics endpoints."""

    def __init__(self, host: str, port: int, state: HealthState) -> None:
        self._state = state
        handler = type("ProbeHandler", (_ProbeRequestHandler,), {"state": state})
        self._server = ThreadingHTTPServer((host, port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)
