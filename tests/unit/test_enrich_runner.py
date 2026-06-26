from __future__ import annotations

from datetime import timedelta

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.interfaces import Enricher
from sitefinder.core.models import (
    Business,
    Location,
    Provenance,
    QueryCriteria,
    Rating,
    WebPresence,
    utcnow,
)
from sitefinder.database.repository import SqliteRepository
from sitefinder.enricher.runner import prioritize, run_enrichment
from sitefinder.website_checker.presence import PresenceChecker


def _b(name, osm, status=WebsiteStatus.NONE, website=None, lat=48.2, enriched_days_ago=None):
    prov = Provenance(discovered_by=SourceName.OSM, source_ids={"osm": osm})
    if enriched_days_ago is not None:
        prov.last_enriched = utcnow() - timedelta(days=enriched_days_ago)
    return Business(
        name=name,
        category="dentist",
        location=Location(latitude=lat, longitude=16.3, postal_code="1070", district=7),
        web_presence=WebPresence(status=status, website_osm=website, effective_website=website),
        provenance=prov,
    )


class _FakeEnricher(Enricher):
    name = SourceName.GOOGLE_PLACES

    def __init__(self):
        self.calls = 0

    def supports(self, business):
        return business.location.latitude is not None

    def enrich(self, business):
        self.calls += 1
        business.rating = Rating(score=4.5, review_count=20, source=SourceName.GOOGLE_PLACES)
        business.provenance.source_ids["google_places"] = "ChIJ" + business.provenance.source_ids["osm"]
        business.provenance.last_enriched = utcnow()
        return business


def test_prioritize_orders_by_presence_then_name():
    items = [
        _b("Z has", "n1", status=WebsiteStatus.HAS_SITE),
        _b("A none", "n2", status=WebsiteStatus.NONE),
        _b("B social", "n3", status=WebsiteStatus.SOCIAL_ONLY),
    ]
    ordered = [b.web_presence.status for b in prioritize(items)]
    assert ordered == [WebsiteStatus.NONE, WebsiteStatus.SOCIAL_ONLY, WebsiteStatus.HAS_SITE]


def _seed(repo, businesses):
    for b in businesses:
        repo.upsert(b)


def test_run_enrichment_respects_top_and_priority():
    repo = SqliteRepository(":memory:")
    _seed(
        repo,
        [
            _b("Has Site", "n1", status=WebsiteStatus.HAS_SITE, website="https://x.at"),
            _b("No Web A", "n2", status=WebsiteStatus.NONE),
            _b("No Web B", "n3", status=WebsiteStatus.NONE),
        ],
    )
    enricher = _FakeEnricher()
    result = run_enrichment(repo, enricher, PresenceChecker(), "dentist", 7, top=2, freshness_days=30)

    assert result.total == 3
    assert result.selected == 2
    assert result.enriched == 2
    assert enricher.calls == 2  # only the 2 no-website leads, not the has-site one
    enriched = [b for b in repo.find(QueryCriteria()) if "google_places" in b.provenance.source_ids]
    assert {b.name for b in enriched} == {"No Web A", "No Web B"}


def test_run_enrichment_uses_cache_for_fresh():
    repo = SqliteRepository(":memory:")
    _seed(repo, [_b("Fresh", "n1", status=WebsiteStatus.NONE, enriched_days_ago=1)])
    enricher = _FakeEnricher()
    result = run_enrichment(repo, enricher, PresenceChecker(), "dentist", 7, top=5, freshness_days=30)
    assert result.cached == 1
    assert result.enriched == 0
    assert enricher.calls == 0  # fresh -> no API call


def test_run_enrichment_reclassifies_when_website_found():
    repo = SqliteRepository(":memory:")
    _seed(repo, [_b("No Web", "n1", status=WebsiteStatus.NONE)])

    class WebsiteEnricher(_FakeEnricher):
        def enrich(self, business):
            super().enrich(business)
            business.web_presence.website_google = "https://found-by-google.at"
            return business

    run_enrichment(repo, WebsiteEnricher(), PresenceChecker(), "dentist", 7, top=1, freshness_days=30)
    updated = repo.find(QueryCriteria())[0]
    assert updated.web_presence.status is WebsiteStatus.HAS_SITE
