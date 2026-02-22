import asyncio
import logging
import os
from typing import Optional, Dict, Any

import aiohttp

logger = logging.getLogger(__name__)

_BASE_URL = 'https://api.checko.ru/v2'
_TIMEOUT = aiohttp.ClientTimeout(total=int(os.environ.get('HTTP_TIMEOUT_SECONDS', '15')))
_MAX_RETRIES = int(os.environ.get('HTTP_RETRY_COUNT', '2'))

_CB_THRESHOLD = 5
_CB_TIMEOUT_SEC = 60


class CheckoError(Exception):
    pass


class CheckoClient:
    def __init__(self, api_key: str):
        self._key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        # Per-instance circuit breaker state
        self._cb_failures = 0
        self._cb_open_until = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=20, keepalive_timeout=30)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=_TIMEOUT,
                headers={'Accept': 'application/json'},
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        now = asyncio.get_event_loop().time()
        if self._cb_failures >= _CB_THRESHOLD and now < self._cb_open_until:
            logger.warning("Checko circuit breaker open, skipping request")
            return None

        params = {**params, 'key': self._key}
        url = f'{_BASE_URL}/{endpoint}'
        attempt = 0
        delay = 1.0
        while attempt <= _MAX_RETRIES:
            try:
                session = await self._get_session()
                async with session.get(url, params=params) as resp:
                    if resp.status == 429:
                        logger.warning("Checko 429 on %s, attempt %d", endpoint, attempt)
                        await asyncio.sleep(delay)
                        delay *= 2
                        attempt += 1
                        continue
                    if resp.status >= 500:
                        self._cb_failures += 1
                        if self._cb_failures >= _CB_THRESHOLD:
                            self._cb_open_until = now + _CB_TIMEOUT_SEC
                        logger.error("Checko 5xx %d on %s", resp.status, endpoint)
                        return None
                    resp.raise_for_status()
                    self._cb_failures = 0
                    body = await resp.json(content_type=None)
                    if body.get('code') == 1:
                        return body.get('data')
                    logger.info("Checko %s returned code=%s", endpoint, body.get('code'))
                    return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Checko %s error: %s", endpoint, e)
                self._cb_failures += 1
                if self._cb_failures >= _CB_THRESHOLD:
                    self._cb_open_until = now + _CB_TIMEOUT_SEC
                attempt += 1
                if attempt <= _MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= 2
        return None

    async def get_company(self, inn: str) -> Optional[Dict]:
        return await self._request('company', {'inn': inn})

    async def get_entrepreneur(self, inn: str) -> Optional[Dict]:
        return await self._request('entrepreneur', {'inn': inn})

    async def get_finances(self, inn: str) -> Optional[Dict]:
        return await self._request('finances', {'inn': inn, 'extended': 'true'})

    async def get_arbitrage(self, inn: str) -> Optional[Dict]:
        return await self._request('arbitrage', {'inn': inn})

    async def get_fssp(self, inn: str) -> Optional[Dict]:
        return await self._request('fssp', {'inn': inn})

    async def get_inspections(self, inn: str) -> Optional[Dict]:
        return await self._request('inspections', {'inn': inn})

    async def get_contracts(self, inn: str) -> Optional[Dict]:
        return await self._request('contracts', {'inn': inn})
