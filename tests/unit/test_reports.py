from __future__ import annotations

from sitefinder.core.enums import SourceName
from sitefinder.core.models import RunReport
from sitefinder.reports.validation import ValidationReporter


def _report() -> RunReport:
    return RunReport(
        run_id="20260626T140511-d7-dentist",
        category="dentist",
        district=7,
        source=SourceName.OSM,
        collected=134,
        duplicates_removed=6,
        persisted=128,
        no_website=18,
        social_only=24,
        has_website=86,
        enriched=42,
        not_enriched=86,
        potential_leads=42,
        duration_seconds=138.0,
    )


def test_render_contains_key_metrics():
    text = ValidationReporter().render(_report())
    assert "Category: dentist" in text
    assert "Businesses Collected: 134" in text
    assert "Potential Leads: 42" in text
    assert "2m 18s" in text
    assert "Run ID:       20260626T140511-d7-dentist" in text


def test_render_writes_file(tmp_path):
    path = tmp_path / "report.txt"
    ValidationReporter().render(_report(), path)
    assert path.read_text(encoding="utf-8").startswith("Category: dentist")
