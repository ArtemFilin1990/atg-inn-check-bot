import datetime as dt
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_NPD_URL = 'https://statusnpd.nalog.ru/api/v1/tracker/taxpayer_status'


class NalogClient:
    """Client for checking self-employed (самозанятый) status via npd.nalog.ru."""

    def __init__(self, timeout: int = 10):
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def check_selfemployed(self, inn: str, date: Optional[dt.date] = None) -> Dict:
        """Return {'status': bool, 'message': str} or {} on error."""
        date = date or dt.date.today()
        try:
            resp = await self._client.post(
                _NPD_URL,
                json={'inn': inn, 'requestDate': date.isoformat()},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("NPD HTTP error %s for INN %s", e.response.status_code, inn)
            return {}
        except httpx.RequestError as e:
            logger.error("NPD network error for INN %s: %s", inn, e)
            return {}
        except Exception as e:
            logger.exception("NPD check error for INN %s: %s", inn, e)
            return {}
