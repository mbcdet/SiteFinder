from __future__ import annotations

from sitefinder.analyzer import htmlutils
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class MobileFriendlinessChecker(Checker):
    """Responsive intent via the viewport meta tag (the single strongest, cheaply-detectable
    mobile signal in static HTML)."""

    name = "mobile_friendly"
    weight = 1.5

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.html:
            return self._result(0.0, "no HTML to inspect")
        if htmlutils.has_viewport(snapshot.html):
            return self._result(1.0, "responsive viewport meta present")
        return self._result(0.0, "no viewport meta (likely not mobile-friendly)")
