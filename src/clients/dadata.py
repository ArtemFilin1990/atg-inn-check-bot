import logging
import os
from typing import Optional, Dict, List, Any

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
    async def _find_by_id(self, query: str, **kwargs: Any) -> List[Dict]:
        return await self._client.find_by_id(name='party', query=query, **kwargs)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(_RETRY_COUNT + 1),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _find_by_email_raw(self, email: str) -> List[Dict]:
        return await self._client.find_by_email(name='party', query=email)

    async def find_by_email(self, email: str) -> List[Dict]:
        """Find companies by email address. Returns list of suggestions."""
        try:
            return await self._find_by_email_raw(email)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 403:
                logger.error("DaData daily quota exceeded (403) for email %s", email)
            else:
                logger.error("DaData HTTP error %s for email %s", status, email)
            return []
        except httpx.RequestError as e:
            logger.error("DaData network error for email %s: %s", email, e)
            return []
        except Exception as e:
            logger.exception("DaData find_by_email error for %s: %s", email, e)
            return []

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(_RETRY_COUNT + 1),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _find_affiliated_raw(self, inn: str, *, count: int = 20, scope: Optional[str] = None) -> List[Dict]:
        kwargs = {'query': inn, 'count': count}
        if scope:
            kwargs['scope'] = scope
        return await self._client.find_affiliated(**kwargs)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(_RETRY_COUNT + 1),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _suggest_party_raw(self, query: str, count: int = 10) -> List[Dict]:
        return await self._client.suggest(name='party', query=query, count=count)

    async def find_affiliated(self, inn: str, *, count: int = 20, scope: Optional[str] = None) -> List[Dict]:
        """Find affiliated companies by INN. Returns list of suggestions."""
        try:
            return await self._find_affiliated_raw(inn=inn, count=count, scope=scope)
        except httpx.HTTPStatusError as e:
            logger.error("DaData HTTP error %s for affiliated %s", e.response.status_code, inn)
            return []
        except httpx.RequestError as e:
            logger.error("DaData network error for affiliated %s: %s", inn, e)
            return []
        except Exception as e:
            logger.exception("DaData find_affiliated error for %s: %s", inn, e)
            return []

    async def find_by_id_party(self, query: str, **kwargs: Any) -> List[Dict]:
        """Find company/IP by INN/OGRN with all supported findById parameters."""
        try:
            return await self._find_by_id(query, **kwargs)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 403:
                logger.error("DaData daily quota exceeded (403) for query %s", query)
            elif status == 429:
                logger.warning("DaData rate limit hit (429) for query %s", query)
            else:
                logger.error("DaData HTTP error %s for query %s", status, query)
            return []
        except httpx.RequestError as e:
            logger.error("DaData network error for query %s: %s", query, e)
            return []
        except Exception as e:
            logger.exception("DaData find_by_id error for %s: %s", query, e)
            return []

    async def suggest_party(self, query: str, count: int = 10) -> List[Dict]:
        """Suggest companies/IPs by free-text query (e.g. person full name)."""
        try:
            return await self._suggest_party_raw(query=query, count=count)
        except httpx.HTTPStatusError as e:
            logger.error("DaData suggest HTTP error %s for query %s", e.response.status_code, query)
            return []
        except httpx.RequestError as e:
            logger.error("DaData suggest network error for query %s: %s", query, e)
            return []
        except Exception as e:
            logger.exception("DaData suggest error for %s: %s", query, e)
            return []

    async def find_party(self, query: str) -> Optional[Dict]:
        """Find company or IP by INN or OGRN. Returns first suggestion or None."""
        suggestions = await self.find_by_id_party(query=query, branch_type='MAIN')
        return suggestions[0] if suggestions else None
