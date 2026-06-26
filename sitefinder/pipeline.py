from __future__ import annotations

import time

from sitefinder.collector.dedup import deduplicate
from sitefinder.core.enums import WebsiteStatus
from sitefinder.core.interfaces import DataSource, Enricher, Repository, WebsiteChecker
from sitefinder.core.models import Business, DiscoveryQuery, RunReport, utcnow
from sitefinder.infra.logging import get_logger

log = get_logger(__name__)


class Pipeline:
    """Orchestrates a single run: discover -> dedup -> (optional enrich) -> classify ->
    persist, assembling a RunReport. Depends only on interfaces; holds no source-specific logic."""

    def __init__(
        self,
        source: DataSource,
        checker: WebsiteChecker,
        repository: Repository,
        enricher: Enricher | None = None,
        freshness_days: int = 30,
    ) -> None:
        self._source = source
        self._checker = checker
        self._repo = repository
        self._enricher = enricher
        self._freshness_days = freshness_days

    def run(self, query: DiscoveryQuery) -> RunReport:
        started = utcnow()
        clock = time.monotonic()

        discovered = list(self._source.discover(query))
        unique, duplicates = deduplicate(discovered)

        if self._enricher is not None:
            unique = [self._maybe_enrich(b) for b in unique]

        for business in unique:
            business.web_presence = self._checker.classify(business)

        for business in unique:
            self._repo.upsert(business)

        report = self._build_report(query, started, clock, len(discovered), duplicates, unique)
        self._repo.save_report(report)
        log.info(
            "Run complete: %d collected, %d persisted, %d potential leads",
            report.collected,
            report.persisted,
            report.potential_leads,
        )
        return report

    def _is_fresh(self, business: Business) -> bool:
        last = business.provenance.last_enriched
        return last is not None and (utcnow() - last).days < self._freshness_days

    def _maybe_enrich(self, business: Business) -> Business:
        """Enrich survivors only, reusing fresh cached data to stay within API budget."""
        if not self._enricher.supports(business):
            return business
        existing = self._repo.find_match(business)
        if existing is not None and self._is_fresh(existing):
            business.rating = existing.rating
            business.provenance.last_enriched = existing.provenance.last_enriched
            if "google_places" in existing.provenance.source_ids:
                business.provenance.source_ids["google_places"] = existing.provenance.source_ids[
                    "google_places"
                ]
            if existing.web_presence.website_google:
                business.web_presence.website_google = existing.web_presence.website_google
            return business
        return self._enricher.enrich(business)

    def _build_report(
        self,
        query: DiscoveryQuery,
        started,
        clock: float,
        collected: int,
        duplicates: int,
        unique: list[Business],
    ) -> RunReport:
        no_website = sum(1 for b in unique if b.web_presence.status is WebsiteStatus.NONE)
        social_only = sum(1 for b in unique if b.web_presence.status is WebsiteStatus.SOCIAL_ONLY)
        has_website = sum(1 for b in unique if b.web_presence.status is WebsiteStatus.HAS_SITE)
        enriched = sum(1 for b in unique if "google_places" in b.provenance.source_ids)
        finished = utcnow()
        run_id = f"{started:%Y%m%dT%H%M%S}-d{query.district}-{query.category}"
        return RunReport(
            run_id=run_id,
            category=query.category,
            district=query.district,
            source=self._source.name,
            enricher=self._enricher.name if self._enricher else None,
            collected=collected,
            duplicates_removed=duplicates,
            persisted=len(unique),
            no_website=no_website,
            social_only=social_only,
            has_website=has_website,
            enriched=enriched,
            not_enriched=len(unique) - enriched,
            potential_leads=no_website + social_only,
            started_at=started,
            finished_at=finished,
            duration_seconds=round(time.monotonic() - clock, 2),
        )
