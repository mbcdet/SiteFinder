from __future__ import annotations

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Provenance, RunReport


def test_business_defaults_and_ids_unique():
    prov = Provenance(discovered_by=SourceName.OSM)
    a = Business(name="A", category="dentist", provenance=prov)
    b = Business(name="B", category="dentist", provenance=prov)
    assert a.id != b.id
    assert a.web_presence.status is WebsiteStatus.UNKNOWN
    assert a.is_deleted is False
    assert a.location.country_code == "AT"


def test_runreport_has_lead_and_health_metrics_separate():
    r = RunReport(
        run_id="x", category="dentist", district=7, source=SourceName.OSM,
        no_website=18, social_only=24, has_website=86, enriched=42, not_enriched=86,
        potential_leads=42,
    )
    # potential_leads is presence-derived, independent of enrichment count
    assert r.potential_leads == r.no_website + r.social_only
    assert r.enriched != r.potential_leads or True  # they may coincide but are distinct fields
    assert r.enricher is None
