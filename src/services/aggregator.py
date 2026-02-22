import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# TTL constants in seconds
TTL_CARD = 12 * 3600          # main card: 12 hours
TTL_SECTION = 24 * 3600       # courts / debts / checks: 24 hours
TTL_FINANCES = 7 * 24 * 3600  # finances: 7 days


class Aggregator:
    """Merge Checko (primary truth) + DaData (enrichment)."""

    def __init__(self, checko, dadata, cache, ref_data):
        self.checko = checko
        self.dadata = dadata
        self.cache = cache
        self.ref = ref_data

    async def get_card(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch and merge main card data. query = INN (10/12) or OGRN (13)."""
        cache_key = f'card|{query}'
        cached = await self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for card %s", query)
            return cached

        # Determine entity type by length
        is_individual = len(query) == 12

        if is_individual:
            checko_data = await self.checko.get_entrepreneur(query)
        else:
            checko_data = await self.checko.get_company(query)

        dadata_data = await self.dadata.find_party(query)

        if not checko_data and not dadata_data:
            return None

        # Enrich OKVED name from reference data
        okved_code = None
        if checko_data:
            okved_code = checko_data.get('okved')
        if not okved_code and dadata_data:
            okved_code = (dadata_data.get('data') or {}).get('okved')
        if okved_code:
            okved_name = await self.ref.get_okved_name(okved_code)
            if okved_name:
                if checko_data is None:
                    checko_data = {}
                checko_data['okved_name'] = okved_name

        result = {
            'query': query,
            'checko': checko_data or {},
            'dadata': dadata_data or {},
            'is_individual': is_individual,
        }
        # Resolved INN from response (for sub-query callbacks)
        resolved_inn = (
            (checko_data or {}).get('inn')
            or ((dadata_data or {}).get('data') or {}).get('inn')
            or query
        )
        result['inn'] = resolved_inn

        await self.cache.set(cache_key, result, TTL_CARD)
        return result

    async def get_section(self, inn: str, section: str) -> Dict[str, Any]:
        """Fetch a lazy section (courts, debts, etc.)."""
        cache_key = f'section|{section}|{inn}'
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        data: Dict[str, Any] = {}
        ttl = TTL_SECTION

        if section == 'courts':
            raw = await self.checko.get_arbitrage(inn)
            data = _parse_courts(raw)
        elif section == 'debts':
            raw = await self.checko.get_fssp(inn)
            data = _parse_debts(raw)
        elif section == 'checks':
            raw = await self.checko.get_inspections(inn)
            data = _parse_checks(raw)
        elif section == 'bankruptcy':
            raw = await self.checko.get_company(inn)
            data = _parse_bankruptcy(raw)
        elif section == 'tenders':
            raw = await self.checko.get_contracts(inn)
            data = _parse_tenders(raw)
        elif section == 'finance':
            raw = await self.checko.get_finances(inn)
            data = _parse_finance(raw)
            ttl = TTL_FINANCES
        elif section == 'connections':
            raw = await self.checko.get_company(inn)
            data = _parse_connections(raw)
        elif section == 'risks':
            card = await self.cache.get(f'card|{inn}')
            if card is None:
                card = await self.get_card(inn)
            data = _parse_risks(card)

        await self.cache.set(cache_key, data, ttl)
        return data


# ── section parsers ───────────────────────────────────────────────────────────

def _parse_courts(raw) -> dict:
    if raw is None:
        return {}
    cases_raw = raw.get('cases') or raw.get('items') or []
    cases = []
    for c in cases_raw:
        cases.append({
            'number': c.get('number') or c.get('case_number') or c.get('id'),
            'court': c.get('court') or c.get('court_name'),
            'date': c.get('date') or c.get('start_date'),
            'status': c.get('status'),
            'amount': c.get('amount') or c.get('sum'),
        })
    return {
        'total': raw.get('total') or len(cases),
        'plaintiff_pct': raw.get('plaintiff_pct', 0),
        'defendant_pct': raw.get('defendant_pct', 0),
        'cases': cases,
    }


def _parse_debts(raw) -> dict:
    if not raw:
        return {}
    items_raw = raw.get('items') or raw.get('data') or []
    items = []
    for it in items_raw:
        items.append({
            'date': it.get('date') or it.get('open_date'),
            'subject': it.get('subject') or it.get('reason'),
            'amount': it.get('amount') or it.get('sum'),
            'region': it.get('region'),
        })
    return {
        'total': raw.get('total') or len(items),
        'total_sum': raw.get('total_sum') or raw.get('sum'),
        'items': items,
    }


def _parse_checks(raw) -> dict:
    if not raw:
        return {}
    items_raw = raw.get('items') or []
    items = []
    for it in items_raw:
        items.append({
            'type': it.get('type') or it.get('kind'),
            'period': it.get('period') or it.get('date'),
            'result': it.get('result'),
        })
    return {'total': raw.get('total') or len(items), 'items': items}


def _parse_bankruptcy(raw) -> dict:
    if not raw:
        return {'found': False}
    status = (raw.get('status') or '').upper()
    if status == 'BANKRUPT' or raw.get('bankruptcy'):
        return {
            'found': True,
            'status': raw.get('bankruptcy_status') or 'банкрот',
            'case_number': raw.get('bankruptcy_case'),
            'court': raw.get('bankruptcy_court'),
            'stage': raw.get('bankruptcy_stage'),
            'date': raw.get('bankruptcy_date'),
        }
    return {'found': False}


def _parse_tenders(raw) -> dict:
    if not raw:
        return {}
    items_raw = raw.get('items') or raw.get('contracts') or []
    items = []
    for it in items_raw:
        items.append({
            'number': it.get('number') or it.get('id'),
            'date': it.get('date') or it.get('sign_date'),
            'amount': it.get('amount') or it.get('price'),
            'customer': it.get('customer') or it.get('customer_name'),
        })
    return {
        'total': raw.get('total') or len(items),
        'total_sum': raw.get('total_sum') or raw.get('sum'),
        'items': items,
    }


def _parse_finance(raw) -> dict:
    if not raw:
        return {}
    rows_raw = raw.get('years') or raw.get('rows') or []
    rows = []
    for r in rows_raw:
        rows.append({
            'year': r.get('year'),
            'revenue': r.get('revenue') or r.get('income') or r.get('выручка'),
            'net_profit': r.get('net_profit') or r.get('profit') or r.get('прибыль'),
        })
    return {'rows': rows}


def _parse_connections(raw) -> dict:
    if not raw:
        return {}
    founders_raw = raw.get('founders') or raw.get('owners') or []
    owners = []
    for f in founders_raw:
        owners.append({
            'name': f.get('name') or f.get('fio'),
            'share': f.get('share') or f.get('percent'),
        })
    related_raw = raw.get('related') or raw.get('affiliates') or []
    related = []
    for r in related_raw:
        related.append({
            'name': r.get('name'),
            'inn': r.get('inn'),
            'role': r.get('role'),
        })
    return {'owners': owners, 'related': related}


def _parse_risks(card) -> dict:
    if not card:
        return {}
    dd = (card.get('dadata') or {}).get('data') or {}
    state = dd.get('state') or {}
    return {'state_status': state.get('status') or ''}
