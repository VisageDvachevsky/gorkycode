from __future__ import annotations

import base64
import hashlib
import json
import secrets
from typing import Sequence


def generate_share_token(summary: str, distance: float, minutes: int, poi_ids: Sequence[int]) -> str:
    payload = {
        "s": summary,
        "d": round(distance, 2),
        "t": minutes,
        "p": list(poi_ids),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    salt = secrets.token_bytes(4)
    digest = hashlib.blake2s(raw + salt, digest_size=9).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
