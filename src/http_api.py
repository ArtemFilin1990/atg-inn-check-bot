import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from aiohttp import web

from bot.formatters import validate_inn

logger = logging.getLogger(__name__)

_ALLOWED_ENTITY_TYPES = {'LEGAL', 'INDIVIDUAL'}


class SimpleRateLimiter:
    """A minimal in-memory fixed-window rate limiter."""

    def __init__(self, requests_per_second: float = 1.0):
        self._rps = max(float(requests_per_second), 0.0)
        self._hits: Dict[str, float] = {}

    def allow(self, key: str) -> bool:
        if self._rps <= 0:
            return True

        now = time.monotonic()
        min_delta = 1.0 / self._rps

        # Lightweight stale-entry cleanup to avoid unbounded growth.
        if len(self._hits) > 10_000:
            cutoff = now - max(60.0, min_delta * 2)
            self._hits = {k: ts for k, ts in self._hits.items() if ts >= cutoff}

        last = self._hits.get(key)
        if last is not None and now - last < min_delta:
            return False
        self._hits[key] = now
        return True


class LookupValidationError(ValueError):
    pass


def parse_lookup_params(payload: Dict[str, Any]) -> Tuple[str, Optional[str], int]:
    query_raw = payload.get('query')
    if not isinstance(query_raw, str):
        raise LookupValidationError('query must be a string')
    query_raw = query_raw.strip()
    if len(query_raw) > 64:
        raise LookupValidationError('query is too long')

    query = validate_inn(query_raw)
    if not query:
        raise LookupValidationError('query must be a valid INN/OGRN')

    entity_type_raw = payload.get('entity_type')
    entity_type: Optional[str] = None
    if entity_type_raw is not None:
        if not isinstance(entity_type_raw, str):
            raise LookupValidationError('entity_type must be a string')
        entity_type = entity_type_raw.strip().upper()
        if entity_type not in _ALLOWED_ENTITY_TYPES:
            raise LookupValidationError('entity_type must be LEGAL or INDIVIDUAL')

    if entity_type == 'LEGAL' and len(query) not in (10, 13):
        raise LookupValidationError('LEGAL supports only INN(10) or OGRN(13)')
    if entity_type == 'INDIVIDUAL' and len(query) not in (12, 15):
        raise LookupValidationError('INDIVIDUAL supports only INN(12) or OGRNIP(15)')

    count = payload.get('count', 10)
    if isinstance(count, bool) or not isinstance(count, int):
        raise LookupValidationError('count must be an integer')
    if count < 1 or count > 20:
        raise LookupValidationError('count must be between 1 and 20')

    return query, entity_type, count


def build_lookup_response(card_data: Dict[str, Any]) -> Dict[str, Any]:
    dadata = card_data.get('dadata') or {}
    dd = dadata.get('data') or {}
    name_data = dd.get('name') or {}
    return {
        'query': card_data.get('query', ''),
        'inn': dd.get('inn') or card_data.get('inn') or '',
        'ogrn': dd.get('ogrn') or '',
        'kpp': dd.get('kpp') or '',
        'entity_type': dd.get('type') or '',
        'name': name_data.get('short_with_opf') or name_data.get('full_with_opf') or dadata.get('value') or '',
        'status': (dd.get('state') or {}).get('status') or '',
        'address': (dd.get('address') or {}).get('unrestricted_value') or '',
        'okved': dd.get('okved') or '',
        'okved_name': card_data.get('okved_name') or '',
    }


def _client_ip(request: web.Request) -> str:
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote or 'unknown'


async def health_handler(_: web.Request) -> web.Response:
    return web.json_response({'status': 'ok'})


def create_lookup_handler(aggregator, rate_limiter: SimpleRateLimiter):
    async def lookup_handler(request: web.Request) -> web.Response:
        ip = _client_ip(request)
        if not rate_limiter.allow(ip):
            return web.json_response({'ok': False, 'error': 'rate_limited'}, status=429)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({'ok': False, 'error': 'invalid_json'}, status=400)

        if not isinstance(payload, dict):
            return web.json_response({'ok': False, 'error': 'payload_must_be_object'}, status=400)

        try:
            query, entity_type, count = parse_lookup_params(payload)
        except LookupValidationError as exc:
            return web.json_response({'ok': False, 'error': str(exc)}, status=400)

        card_data = await aggregator.get_card(query, entity_type=entity_type, count=count)
        if not card_data:
            return web.json_response({'ok': False, 'error': 'not_found'}, status=404)

        return web.json_response({'ok': True, 'result': build_lookup_response(card_data)})

    return lookup_handler


def rate_limiter_from_env() -> SimpleRateLimiter:
    raw = os.environ.get('LOOKUP_RATE_LIMIT_RPS', '1')
    try:
        rps = float(raw)
    except ValueError:
        logger.warning('Invalid LOOKUP_RATE_LIMIT_RPS=%r, using default 1', raw)
        rps = 1.0
    if rps < 0:
        logger.warning('Negative LOOKUP_RATE_LIMIT_RPS=%r, using 0', raw)
        rps = 0.0
    return SimpleRateLimiter(requests_per_second=rps)
