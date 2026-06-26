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
        web_presence=WebPresence(status=WebsiteStatus.HAS_SITE, website_url="https://huber.at"),
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
