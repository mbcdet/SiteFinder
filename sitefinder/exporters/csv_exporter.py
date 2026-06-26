from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from sitefinder.core.interfaces import Exporter
from sitefinder.core.models import Business

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


def _maps_url(business: Business) -> str:
    place_id = business.provenance.source_ids.get("google_places")
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""


class CsvExporter(Exporter):
    def export(self, businesses: Iterable[Business], destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_HEADERS)
            for b in businesses:
                rating = b.rating
                writer.writerow(
                    [
                        b.name,
                        b.location.street or "",
                        b.location.postal_code or "",
                        b.location.district or "",
                        b.contact.phone or "",
                        b.web_presence.website_url or "",
                        b.web_presence.status.value,
                        rating.score if rating and rating.score is not None else "",
                        rating.review_count if rating and rating.review_count is not None else "",
                        _maps_url(b),
                        b.provenance.discovered_by.value,
                        b.provenance.last_updated.date().isoformat(),
                    ]
                )
        return destination
