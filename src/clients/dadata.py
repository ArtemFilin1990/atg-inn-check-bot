import logging
import os
from typing import Optional, Dict, List

from dadata import DadataAsync as _DadataAsync

logger = logging.getLogger(__name__)


class DadataClient:
    """Thin wrapper around dadata-py DadataAsync for dependency injection."""

    def __init__(self, token: str, secret: str):
        self._client = _DadataAsync(token, secret)

    async def close(self):
        await self._client.close()

    async def find_party(self, query: str) -> Optional[Dict]:
        """Find company or IP by INN or OGRN. Returns first suggestion or None."""
        try:
            suggestions: List[Dict] = await self._client.find_by_id(
                name='party', query=query, branch_type='MAIN'
            )
            return suggestions[0] if suggestions else None
        except Exception as e:
            logger.exception("DaData find_party error for %s: %s", query, e)
            return None
