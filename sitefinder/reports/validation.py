from __future__ import annotations

from pathlib import Path

from sitefinder.core.interfaces import Reporter
from sitefinder.core.models import RunReport


def _format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}m {secs:02d}s"


class ValidationReporter(Reporter):
    """Renders a RunReport as a human-readable validation summary. Pure presentation."""

    def render(self, report: RunReport, destination: Path | None = None) -> str:
        generated = report.finished_at or report.started_at
        text = "\n".join(
            [
                f"Category: {report.category}",
                f"District: {report.district}",
                "",
                f"Businesses Collected: {report.collected}",
                f"Duplicates Removed:   {report.duplicates_removed}",
                f"Businesses Persisted: {report.persisted}",
                "",
                f"No Website:   {report.no_website}",
                f"Social Only:  {report.social_only}",
                f"Has Website:  {report.has_website}",
                "",
                f"Enriched:     {report.enriched}",
                f"Not Enriched: {report.not_enriched}",
                "",
                f"Potential Leads: {report.potential_leads}    (= No Website + Social Only)",
                "",
                f"Run Duration: {_format_duration(report.duration_seconds)}",
                f"Generated At: {generated.isoformat()}",
                f"Run ID:       {report.run_id}",
            ]
        )
        if destination is not None:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
        return text
