from __future__ import annotations

from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class BrokenLinkChecker(Checker):
    """Practical site-health proxy from the single fetch: reachable, a 2xx/3xx status, and a
    non-trivial body. Full link crawling is deferred (it multiplies requests) — documented."""

    name = "site_health"
    weight = 0.5

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.reachable:
            return self._result(0.0, f"unreachable ({snapshot.error or 'no response'})")
        status = snapshot.status_code or 0
        if status >= 400:
            return self._result(0.0, f"error status {status}")
        if not snapshot.html or len(snapshot.html) < 500:
            return self._result(0.3, "reachable but near-empty page")
        return self._result(1.0, f"healthy ({status})")
