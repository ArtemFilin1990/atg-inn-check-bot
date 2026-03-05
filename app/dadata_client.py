from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

DADATA_FINDBYID_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"

_cache: TTLCache = TTLCache(maxsize=512, ttl=900)  # 15 minutes

_DIGITS_RE = re.compile(r"\D+")


def validate_inn(inn: str) -> bool:
    return bool(re.fullmatch(r"\d{10}|\d{12}", inn))


def validate_ogrn(ogrn: str) -> bool:
    return bool(re.fullmatch(r"\d{13}|\d{15}", ogrn))


def normalize_query_input(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "", "name"

    digits = _DIGITS_RE.sub("", raw)
    if validate_inn(digits):
        return digits, "inn"
    if validate_ogrn(digits):
        return digits, "ogrn"

    return raw, "name"


def _cache_key(endpoint: str, **kwargs: Any) -> str:
    params = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"{endpoint}?{params}"


async def _post_dadata(
    *,
    api_key: str,
    url: str,
    payload: dict[str, Any],
    cache_endpoint: str,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("DADATA api_key must not be empty")

    key = _cache_key(cache_endpoint, **payload)
    if key in _cache:
        logger.debug("cache hit for %s", key)
        return _cache[key]

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, dict):
        raise ValueError("DaData response must be a JSON object")

    _cache[key] = data
    return data


async def find_by_id_party(
    api_key: str,
    query: str,
    branch_type: str | None = None,
    count: int = 10,
    kpp: str | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("DaData query must not be empty")
    if count <= 0:
        raise ValueError("count must be greater than 0")

    payload: dict[str, Any] = {"query": query, "count": count}
    if branch_type:
        payload["branch_type"] = branch_type
    if kpp:
        payload["kpp"] = kpp
    if entity_type:
        payload["type"] = entity_type

    return await _post_dadata(
        api_key=api_key,
        url=DADATA_FINDBYID_URL,
        payload=payload,
        cache_endpoint="findById/party",
    )


async def suggest_party(api_key: str, query: str, count: int = 10) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("DaData query must not be empty")
    if count <= 0:
        raise ValueError("count must be greater than 0")

    payload: dict[str, Any] = {"query": query, "count": count}
    return await _post_dadata(
        api_key=api_key,
        url=DADATA_SUGGEST_URL,
        payload=payload,
        cache_endpoint="suggest/party",
    )


async def find_party_universal(api_key: str, text: str, count: int = 1) -> dict[str, Any]:
    """Always resolve party via suggest first, then enrich via findById/party."""
    query, kind = normalize_query_input(text)
    if not query:
        raise ValueError("DaData query must not be empty")

    suggested = await suggest_party(api_key, query=query, count=count)
    suggestions: list[dict[str, Any]] = suggested.get("suggestions", [])
    if not suggestions:
        if kind in {"inn", "ogrn"}:
            return await find_by_id_party(api_key, query=query, count=count)
        return suggested

    best = suggestions[0].get("data") or {}
    best_query = str(best.get("inn") or best.get("ogrn") or "").strip()
    if not best_query and kind in {"inn", "ogrn"}:
        best_query = query
    if not best_query:
        return suggested

    detailed = await find_by_id_party(api_key, query=best_query, count=1)
    detailed_suggestions = detailed.get("suggestions", [])
    if detailed_suggestions:
        return detailed
    return suggested
