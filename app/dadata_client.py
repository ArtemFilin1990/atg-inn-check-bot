from __future__ import annotations

import re
import logging
from typing import Any

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

DADATA_FINDBYID_URL = (
    "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
)

_cache: TTLCache = TTLCache(maxsize=512, ttl=900)  # 15 minutes


def validate_inn(inn: str) -> bool:
    """Return True if inn is exactly 10 or 12 digits."""
    return bool(re.fullmatch(r"\d{10}|\d{12}", inn))


def _cache_key(**kwargs: Any) -> str:
    return "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def find_by_id_party(
    api_key: str,
    query: str,
    branch_type: str | None = None,
    count: int = 10,
    kpp: str | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    """
    Call DaData findById/party and return the parsed JSON dict.
    Raises httpx.HTTPStatusError on non-2xx responses.
    Raises httpx.TimeoutException on timeout.
    """
    if not api_key.strip():
        raise ValueError("DADATA api_key must not be empty")
    if not query.strip():
        raise ValueError("DaData query must not be empty")
    if count <= 0:
        raise ValueError("count must be greater than 0")

    key = _cache_key(
        query=query,
        branch_type=branch_type or "",
        count=count,
        kpp=kpp or "",
        entity_type=entity_type or "",
    )
    if key in _cache:
        logger.debug("cache hit for %s", query)
        return _cache[key]

    payload: dict[str, Any] = {"query": query, "count": count}
    if branch_type:
        payload["branch_type"] = branch_type
    if kpp:
        payload["kpp"] = kpp
    if entity_type:
        payload["type"] = entity_type

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(DADATA_FINDBYID_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, dict):
        raise ValueError("DaData response must be a JSON object")

    _cache[key] = data
    return data
