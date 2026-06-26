from __future__ import annotations

from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class SslChecker(Checker):
    name = "ssl"
    weight = 1.5

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.reachable:
            return self._result(0.0, "site unreachable")
        if snapshot.is_https:
            return self._result(1.0, "served over HTTPS")
        return self._result(0.0, "no HTTPS (served over HTTP)")
