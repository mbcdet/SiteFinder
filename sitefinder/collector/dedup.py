from __future__ import annotations

import re
from collections.abc import Iterable

from sitefinder.core.models import Business

_WHITESPACE = re.compile(r"\s+")


def _normalize_name(name: str) -> str:
    return _WHITESPACE.sub(" ", name.strip().casefold())


def deduplicate(businesses: Iterable[Business]) -> tuple[list[Business], int]:
    """Remove duplicates, returning (unique_businesses, duplicates_removed).

    Two-level: exact OSM source id, then (normalized name, postal code) to collapse the
    common node/way duplication of a single place. First occurrence wins.
    """
    seen_source_ids: set[str] = set()
    seen_keys: set[tuple[str, str | None]] = set()
    unique: list[Business] = []
    removed = 0

    for business in businesses:
        osm_id = business.provenance.source_ids.get("osm")
        key = (_normalize_name(business.name), business.location.postal_code)
        if (osm_id and osm_id in seen_source_ids) or key in seen_keys:
            removed += 1
            continue
        if osm_id:
            seen_source_ids.add(osm_id)
        seen_keys.add(key)
        unique.append(business)

    return unique, removed
