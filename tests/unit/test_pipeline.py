from __future__ import annotations

from collections.abc import Iterable

from sitefinder.core.enums import SourceName
from sitefinder.core.interfaces import DataSource, Enricher
from sitefinder.core.models import (
    Business,
    DiscoveryQuery,
    Location,
    Provenance,
    QueryCriteria,
    Rating,
    WebPresence,
    utcnow,
)
from sitefinder.database.repository import SqliteRepository
from sitefinder.pipeline import Pipeline
from sitefinder.website_checker.presence import PresenceChecker


def _b(name: str, osm: str, website=None, social=None) -> Business:
    return Business(
        name=name,
        category="dentist",
        location=Location(district=7, postal_code="1070"),
        web_presence=WebPresence(website_url=website, social_urls=social or []),
        provenance=Provenance(discovered_by=SourceName.OSM, source_ids={"osm": osm}),
    )


class _FakeSource(DataSource):
    name = SourceName.OSM

    def __init__(self, businesses: list[Business]) -> None:
        self._businesses = businesses

    def discover(self, query: DiscoveryQuery) -> Iterable[Business]:
        return list(self._businesses)


class _FakeEnricher(Enricher):
    name = SourceName.GOOGLE_PLACES

    def supports(self, business: Business) -> bool:
        return True

    def enrich(self, business: Business) -> Business:
        business.rating = Rating(score=4.5, review_count=10, source=SourceName.GOOGLE_PLACES)
        business.provenance.source_ids["google_places"] = "ChIJx"
        business.provenance.last_enriched = utcnow()
        return business


def _query() -> DiscoveryQuery:
    return DiscoveryQuery(category="dentist", city="Vienna", district=7)


def test_pipeline_counts_and_persistence():
    source = _FakeSource(
        [
            _b("Huber", "node/1", website="https://h.at"),
            _b("Studio", "node/2", social=["https://facebook.com/s"]),
            _b("Klein", "node/3"),
            _b("Huber", "node/1", website="https://h.at"),  # duplicate
        ]
    )
    repo = SqliteRepository(":memory:")
    report = Pipeline(source, PresenceChecker(), repo).run(_query())

    assert report.collected == 4
    assert report.duplicates_removed == 1
    assert report.persisted == 3
    assert (report.no_website, report.social_only, report.has_website) == (1, 1, 1)
    assert report.potential_leads == 2
    assert report.enriched == 0 and report.not_enriched == 3
    assert len(repo.find(QueryCriteria())) == 3


def test_pipeline_enrichment_counts():
    source = _FakeSource([_b("Klein", "node/3"), _b("Huber", "node/1", website="https://h.at")])
    repo = SqliteRepository(":memory:")
    report = Pipeline(source, PresenceChecker(), repo, enricher=_FakeEnricher()).run(_query())
    assert report.enriched == 2
    assert report.not_enriched == 0
    assert report.enricher is SourceName.GOOGLE_PLACES


def test_pipeline_idempotent_across_runs():
    businesses = [_b("Klein", "node/3"), _b("Huber", "node/1", website="https://h.at")]
    repo = SqliteRepository(":memory:")
    Pipeline(_FakeSource(businesses), PresenceChecker(), repo).run(_query())
    Pipeline(_FakeSource(businesses), PresenceChecker(), repo).run(_query())
    assert len(repo.find(QueryCriteria())) == 2  # no duplication on re-run
