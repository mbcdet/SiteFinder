from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sitefinder.audit_pipeline import ScoredLead


def _check_line(name: str, score: float, details: str) -> str:
    mark = "OK " if score >= 0.5 else "XX "
    return f"    [{mark}] {name:16} {score:4.2f}  {details}"


class AuditReporter:
    """Detailed per-business website audit breakdown."""

    def render(self, leads: Iterable[ScoredLead], destination: Path | None = None) -> str:
        blocks: list[str] = ["WEBSITE AUDIT REPORT", "=" * 60, ""]
        for lead in leads:
            b, audit = lead.business, lead.audit
            blocks.append(f"{b.name}  [{b.web_presence.status.value}]")
            if audit.url:
                state = "reachable" if audit.reachable else "UNREACHABLE"
                blocks.append(f"  {audit.url}  ({state})  audit score {audit.audit_score:.0f}/100")
                for c in audit.checks:
                    blocks.append(_check_line(c.name, c.score, c.details))
            else:
                blocks.append("  no website to audit")
            blocks.append("")
        text = "\n".join(blocks)
        if destination is not None:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
        return text
