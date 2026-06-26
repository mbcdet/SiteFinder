from __future__ import annotations

import csv

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import (
    Business,
    Contact,
    Location,
    Provenance,
    Rating,
    WebPresence,
)
from sitefinder.exporters.csv_exporter import CsvExporter


def _biz() -> Business:
    return Business(
        name="Zahnarzt Huber",
        category="dentist",
        location=Location(street="Mariahilfer Straße 10", postal_code="1070", district=7),
        contact=Contact(phone="+43 1 5230000"),
        rating=Rating(score=4.6, review_count=80, source=SourceName.GOOGLE_PLACES),
        web_presence=WebPresence(
            status=WebsiteStatus.HAS_SITE,
            website_osm="https://huber.at",
            effective_website="https://huber.at",
        ),
        provenance=Provenance(
            discovered_by=SourceName.OSM,
            source_ids={"osm": "node/111", "google_places": "ChIJabc"},
        ),
    )


def test_export_writes_headers_and_rows(tmp_path):
    out = CsvExporter().export([_biz()], tmp_path / "leads.csv")
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0][0] == "Business Name"
    record = dict(zip(rows[0], rows[1]))
    assert record["Business Name"] == "Zahnarzt Huber"
    assert record["District"] == "7"
    assert record["Web Presence"] == "has_site"
    assert record["Google Rating"] == "4.6"
    assert "place_id:ChIJabc" in record["Google Maps URL"]


def test_export_empty_writes_header_only(tmp_path):
    out = CsvExporter().export([], tmp_path / "empty.csv")
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert len(rows) == 1


def _scored(business, audit_url, audit_score, lead_score, band, checks=None):
    from sitefinder.analyzer.models import AuditReport
    from sitefinder.audit_pipeline import ScoredLead
    from sitefinder.lead_scoring.models import LeadScore

    audit = AuditReport(
        business_id=business.id, url=audit_url, reachable=audit_url is not None,
        audit_score=audit_score, checks=checks or [],
    )
    score = LeadScore(business_id=business.id, score=lead_score, band=band, reasons=[])
    return ScoredLead(business=business, audit=audit, score=score)


def test_scored_export_appends_summary_columns(tmp_path):
    from sitefinder.analyzer.models import CheckResult
    from sitefinder.core.models import Location, Provenance

    has_site = Business(
        name="HasSite", category="dentist", location=Location(district=7),
        web_presence=WebPresence(status=WebsiteStatus.HAS_SITE, effective_website="https://x.at"),
        provenance=Provenance(discovered_by=SourceName.OSM),
    )
    no_site = Business(
        name="NoSite", category="dentist", location=Location(district=7),
        web_presence=WebPresence(status=WebsiteStatus.NONE),
        provenance=Provenance(discovered_by=SourceName.OSM),
    )
    weak = [CheckResult(name="performance", score=0.1, weight=1.0),
            CheckResult(name="ssl", score=0.0, weight=1.5)]
    leads = [
        _scored(has_site, "https://x.at", 35.0, 45.5, "medium", checks=weak),
        _scored(no_site, None, 0.0, 90.0, "high"),
    ]
    out = CsvExporter().export_scored(leads, tmp_path / "leads.csv")
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0][-4:] == ["Audit Score", "Lead Score", "Priority", "Weak Areas"]

    has = dict(zip(rows[0], rows[1]))
    assert has["Audit Score"] == "35"
    assert has["Lead Score"] == "46"
    assert has["Priority"] == "Medium"
    assert has["Weak Areas"] == "performance, ssl"

    none = dict(zip(rows[0], rows[2]))
    assert none["Audit Score"] == "N/A"  # no website to audit
    assert none["Lead Score"] == "90"
    assert none["Priority"] == "High"


def test_enriched_export_appends_columns(tmp_path):
    out = CsvExporter().export([_biz()], tmp_path / "enriched.csv", enriched=True)
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0][-2:] == ["Place ID", "Enriched At"]
    record = dict(zip(rows[0], rows[1]))
    assert record["Place ID"] == "ChIJabc"
    # base columns still present and unchanged
    assert record["Business Name"] == "Zahnarzt Huber"
    assert record["Web Presence"] == "has_site"
