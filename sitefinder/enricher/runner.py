from __future__ import annotations

from dataclasses import dataclass

from sitefinder.core.enums import WebsiteStatus
from sitefinder.core.interfaces import Enricher, Repository, WebsiteChecker
from sitefinder.core.models import Business, QueryCriteria, utcnow
from sitefinder.infra.logging import get_logger

log = get_logger(__name__)

# Lower rank = higher sales value, so it is enriched first under a --top budget.
_PRESENCE_RANK = {
    WebsiteStatus.NONE: 0,
    WebsiteStatus.SOCIAL_ONLY: 1,
    WebsiteStatus.HAS_SITE: 2,
    WebsiteStatus.UNKNOWN: 3,
}


@dataclass
class EnrichmentResult:
    total: int  # stored leads in the segment
    selected: int  # how many we attempted (<= top)
    enriched: int  # API calls that added data
    cached: int  # skipped because already fresh
    unsupported: int  # missing data needed for matching (e.g. no coords)


@dataclass
class EnrichmentPlan:
    """Pre-flight estimate shown before any API request is sent."""

    total: int
    selected: int
    cached: int
    unsupported: int
    new_requests: int


def prioritize(businesses: list[Business]) -> list[Business]:
    """Order leads so the most sales-relevant (no website, then social-only) come first."""
    return sorted(
        businesses,
        key=lambda b: (_PRESENCE_RANK.get(b.web_presence.status, 9), b.name.casefold()),
    )


def _is_fresh(business: Business, freshness_days: int) -> bool:
    last = business.provenance.last_enriched
    return last is not None and (utcnow() - last).days < freshness_days


def plan_enrichment(
    repository: Repository,
    enricher: Enricher,
    category: str,
    district: int,
    top: int,
    freshness_days: int,
) -> EnrichmentPlan:
    """Compute what an enrichment run would do — without sending any request."""
    businesses = repository.find(QueryCriteria(category=category, district=district))
    selected = prioritize(businesses)[: max(0, top)]
    cached = unsupported = new_requests = 0
    for business in selected:
        if _is_fresh(business, freshness_days):
            cached += 1
        elif not enricher.supports(business):
            unsupported += 1
        else:
            new_requests += 1
    return EnrichmentPlan(
        total=len(businesses),
        selected=len(selected),
        cached=cached,
        unsupported=unsupported,
        new_requests=new_requests,
    )


def run_enrichment(
    repository: Repository,
    enricher: Enricher,
    checker: WebsiteChecker,
    category: str,
    district: int,
    top: int,
    freshness_days: int,
) -> EnrichmentResult:
    """Enrich the top-N stored leads of a segment. Reads from the repository (the source of
    truth populated by discovery) — never re-runs OSM. Persists results so repeated runs reuse
    the cache instead of re-calling the API."""
    businesses = repository.find(QueryCriteria(category=category, district=district))
    selected = prioritize(businesses)[: max(0, top)]

    enriched = cached = unsupported = 0
    for business in selected:
        if _is_fresh(business, freshness_days):
            cached += 1
            continue
        if not enricher.supports(business):
            unsupported += 1
            continue
        enricher.enrich(business)
        # Places may reveal a website OSM lacked — re-classify so presence stays accurate.
        business.web_presence = checker.classify(business)
        repository.upsert(business)
        enriched += 1

    log.info(
        "Enrichment: %d/%d selected, %d enriched, %d cached, %d unsupported",
        len(selected),
        len(businesses),
        enriched,
        cached,
        unsupported,
    )
    return EnrichmentResult(
        total=len(businesses),
        selected=len(selected),
        enriched=enriched,
        cached=cached,
        unsupported=unsupported,
    )
