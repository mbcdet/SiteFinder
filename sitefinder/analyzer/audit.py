from __future__ import annotations

from collections.abc import Callable, Sequence

from sitefinder.analyzer.checkers import default_checkers
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import AuditReport, CheckResult, SiteSnapshot
from sitefinder.analyzer.snapshot import fetch_snapshot
from sitefinder.core.models import Business

Fetcher = Callable[[str], SiteSnapshot]


class WebsiteAuditor:
    """Fetches a lead's effective website once and runs every checker over the snapshot,
    aggregating a weighted audit score. A thin orchestrator — all logic lives in the checkers."""

    def __init__(
        self,
        checkers: Sequence[Checker] | None = None,
        timeout: float = 15.0,
        fetcher: Fetcher | None = None,
    ) -> None:
        self._checkers = list(checkers) if checkers is not None else default_checkers()
        self._fetch: Fetcher = fetcher or (lambda url: fetch_snapshot(url, timeout))

    def audit(self, business: Business) -> AuditReport:
        url = business.web_presence.effective_website
        if not url:
            # No website to audit; presence already captures this (a strong lead signal).
            return AuditReport(business_id=business.id, url=None, reachable=False, audit_score=0.0)
        snapshot = self._fetch(url)
        results = [checker.check(snapshot) for checker in self._checkers]
        return AuditReport(
            business_id=business.id,
            url=snapshot.final_url or url,
            reachable=snapshot.reachable,
            audit_score=self._aggregate(results),
            checks=results,
        )

    @staticmethod
    def _aggregate(results: list[CheckResult]) -> float:
        applicable = [r for r in results if r.applicable]
        total_weight = sum(r.weight for r in applicable)
        if not total_weight:
            return 0.0
        weighted = sum(r.score * r.weight for r in applicable)
        return round(100 * weighted / total_weight, 1)
