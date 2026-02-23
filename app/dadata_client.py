import os
import httpx
from cachetools import TTLCache
from typing import Optional

DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"

_cache: TTLCache = TTLCache(maxsize=512, ttl=3600)


class DaDataClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def find_by_inn(self, inn: str, count: int = 1) -> Optional[dict]:
        """Fetch company data from DaData by INN. Returns suggestion dict or None."""
        cache_key = f"inn:{inn}:{count}"
        if cache_key in _cache:
            return _cache[cache_key]

        payload = {"query": inn, "count": count}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(DADATA_URL, json=payload, headers=self._headers)

        if resp.status_code == 401:
            raise PermissionError("DaData: неверный API-ключ (401)")
        if resp.status_code == 403:
            raise PermissionError("DaData: доступ запрещён (403)")
        if resp.status_code == 429:
            raise RuntimeError("DaData: превышен лимит запросов (429)")
        resp.raise_for_status()

        data = resp.json()
        suggestions = data.get("suggestions", [])
        result = suggestions if count > 1 else (suggestions[0] if suggestions else None)
        _cache[cache_key] = result
        return result

    async def get_branches(self, inn: str) -> list:
        """Fetch branches (filials) for a given INN."""
        cache_key = f"branches:{inn}"
        if cache_key in _cache:
            return _cache[cache_key]

        payload = {"query": inn, "count": 20, "branch_type": "BRANCH"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(DADATA_URL, json=payload, headers=self._headers)

        if resp.status_code == 401:
            raise PermissionError("DaData: неверный API-ключ (401)")
        if resp.status_code == 403:
            raise PermissionError("DaData: доступ запрещён (403)")
        if resp.status_code == 429:
            raise RuntimeError("DaData: превышен лимит запросов (429)")
        resp.raise_for_status()

        branches = resp.json().get("suggestions", [])
        _cache[cache_key] = branches
        return branches
