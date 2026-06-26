from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from sitefinder.core.interfaces import Exporter
from sitefinder.core.models import Business

if TYPE_CHECKING:  # avoid a runtime dependency on the Phase 2 orchestrator
    from sitefinder.audit_pipeline import ScoredLead

_HEADERS = [
    "Business Name",
    "Address",
    "Postal Code",
    "District",
    "Phone",
    "Website",
    "Web Presence",
    "Google Rating",
    "Review Count",
    "Google Maps URL",
    "Discovered By",
    "Last Updated",
]

# Appended (not replacing) for enriched exports.
_ENRICHMENT_HEADERS = ["Google Website", "Website Match", "Place ID", "Enriched At"]

# Appended after the audit: a compact, sortable summary (details stay in audit_report.txt).
_SUMMARY_HEADERS = ["Audit Score", "Lead Score", "Priority", "Weak Areas"]


def _maps_url(business: Business) -> str:
    place_id = business.provenance.source_ids.get("google_places")
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""


def _base_cells(b: Business) -> list:
    rating = b.rating
    return [
        b.name,
        b.location.street or "",
        b.location.postal_code or "",
        b.location.district or "",
        b.contact.phone or "",
        b.web_presence.effective_website or "",
        b.web_presence.status.value,
        rating.score if rating and rating.score is not None else "",
        rating.review_count if rating and rating.review_count is not None else "",
        _maps_url(b),
        b.provenance.discovered_by.value,
        b.provenance.last_updated.date().isoformat(),
    ]


def _enrichment_cells(b: Business) -> list:
    last_enriched = b.provenance.last_enriched
    return [
        b.web_presence.website_google or "",
        b.web_presence.website_match.value,
        b.provenance.source_ids.get("google_places", ""),
        last_enriched.date().isoformat() if last_enriched else "",
    ]


def _summary_cells(lead: ScoredLead) -> list:
    audit, score = lead.audit, lead.score
    # No website to audit -> N/A audit score, but keep the lead score and priority.
    audit_score = "N/A" if audit.url is None else f"{audit.audit_score:.0f}"
    weak = ", ".join(c.name for c in audit.checks if c.applicable and c.score < 0.5)
    return [audit_score, f"{score.score:.0f}", score.band.capitalize(), weak]


class CsvExporter(Exporter):
    def export(
        self, businesses: Iterable[Business], destination: Path, enriched: bool = False
    ) -> Path:
        """Write leads to CSV (no audit summary). With ``enriched=True`` adds Google columns."""
        headers = _HEADERS + (_ENRICHMENT_HEADERS if enriched else [])
        rows = (
            _base_cells(b) + (_enrichment_cells(b) if enriched else []) for b in businesses
        )
        return self._write(destination, headers, rows)

    def export_scored(
        self, leads: Iterable[ScoredLead], destination: Path, enriched: bool = False
    ) -> Path:
        """Write leads with a compact audit summary (Audit Score, Lead Score, Priority,
        Weak Areas) appended — keeps leads.csv sortable while details live in audit_report.txt."""
        headers = _HEADERS + (_ENRICHMENT_HEADERS if enriched else []) + _SUMMARY_HEADERS
        rows = (
            _base_cells(lead.business)
            + (_enrichment_cells(lead.business) if enriched else [])
            + _summary_cells(lead)
            for lead in leads
        )
        return self._write(destination, headers, rows)

    @staticmethod
    def _write(destination: Path, headers: list, rows: Iterable[list]) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        return destination
