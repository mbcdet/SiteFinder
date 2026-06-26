from __future__ import annotations

from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class PerformanceChecker(Checker):
    """Coarse load-time proxy from the single fetch (full Lighthouse-style metrics are future)."""

    name = "performance"
    weight = 1.0

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.reachable or snapshot.elapsed_ms is None:
            return self._result(0.0, "site unreachable")
        ms = snapshot.elapsed_ms
        if ms < 800:
            score = 1.0
        elif ms < 2000:
            score = 0.7
        elif ms < 4000:
            score = 0.4
        else:
            score = 0.1
        return self._result(score, f"first response in {ms:.0f} ms")
