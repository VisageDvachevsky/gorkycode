import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RouteShareStore:
    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None

    async def _client(self) -> redis.Redis:
        if not self._client:
            try:
                self._client = await redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info("Share store connected to Redis")
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Failed to connect to Redis for share store: %s", exc)
                raise
        return self._client

    async def save_route(self, token: str, payload: Dict[str, Any]) -> None:
        if not token:
            return
        try:
            client = await self._client()
            key = self._key(token)
            await client.set(key, json.dumps(payload, ensure_ascii=False), ex=settings.SHARE_TTL_SECONDS)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to persist shared route %s: %s", token, exc)

    async def load_route(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        try:
            client = await self._client()
            raw = await client.get(self._key(token))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to load shared route %s: %s", token, exc)
            return None

    async def extend_ttl(self, token: str) -> None:
        if not token:
            return
        try:
            client = await self._client()
            await client.expire(self._key(token), settings.SHARE_TTL_SECONDS)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to extend TTL for %s: %s", token, exc)

    def _key(self, token: str) -> str:
        return f"share:route:{token}"


share_store = RouteShareStore()
