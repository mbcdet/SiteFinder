from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sitefinder.audit_pipeline import ScoredLead


class FinalReporter:
    """Ranked, human-readable lead list (best web-dev prospects first)."""

    def render(
        self,
        leads: Sequence[ScoredLead],
        category: str,
        district: int,
        destination: Path | None = None,
    ) -> str:
        high = sum(1 for x in leads if x.score.band == "high")
        medium = sum(1 for x in leads if x.score.band == "medium")

        lines = [
            f"FINAL LEAD REPORT — {category}, district {district}",
            "=" * 60,
            f"Total leads: {len(leads)}   High: {high}   Medium: {medium}",
            "",
        ]
        for rank, lead in enumerate(leads, start=1):
            b, s = lead.business, lead.score
            phone = b.contact.phone or "-"
            rating = ""
            if b.rating and b.rating.score is not None:
                rating = f"  ★{b.rating.score} ({b.rating.review_count or 0})"
            lines.append(
                f"{rank:>3}. [{s.band.upper():6}] {s.score:5.1f}  {b.name}{rating}"
            )
            lines.append(f"       {b.location.street or ''}  ·  {phone}")
            lines.append(f"       {'; '.join(s.reasons)}")
            lines.append("")

        text = "\n".join(lines)
        if destination is not None:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
        return text
