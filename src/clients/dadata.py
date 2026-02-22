import logging
import os
from typing import Optional, Dict, List

import httpx
from dadata import DadataAsync as _DadataAsync
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logger = logging.getLogger(__name__)

_TIMEOUT = int(os.environ.get('HTTP_TIMEOUT_SECONDS', '5'))
_RETRY_COUNT = int(os.environ.get('HTTP_RETRY_COUNT', '2'))


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return True
    return False


class DadataClient:
    """Thin wrapper around dadata-py DadataAsync for dependency injection."""

    def __init__(self, token: str, secret: str):
        self._client = _DadataAsync(token, secret, timeout=_TIMEOUT)

    async def close(self):
        await self._client.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(_RETRY_COUNT + 1),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _find_by_id(self, query: str) -> List[Dict]:
        return await self._client.find_by_id(name='party', query=query, branch_type='MAIN')

    async def find_party(self, query: str) -> Optional[Dict]:
        """Find company or IP by INN or OGRN. Returns first suggestion or None."""
        try:
            suggestions: List[Dict] = await self._find_by_id(query)
            return suggestions[0] if suggestions else None
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 403:
                logger.error("DaData daily quota exceeded (403) for query %s", query)
            elif status == 429:
                logger.warning("DaData rate limit hit (429) for query %s", query)
            else:
                logger.error("DaData HTTP error %s for query %s", status, query)
            return None
        except httpx.RequestError as e:
            logger.error("DaData network error for query %s: %s", query, e)
            return None
        except Exception as e:
            logger.exception("DaData find_party error for %s: %s", query, e)
            return None
