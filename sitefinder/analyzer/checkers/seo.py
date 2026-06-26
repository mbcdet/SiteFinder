from __future__ import annotations

from sitefinder.analyzer import htmlutils
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class SeoChecker(Checker):
    """Basic on-page SEO hygiene: title, meta description, an h1, and a lang attribute."""

    name = "seo_basics"
    weight = 1.0

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.html:
            return self._result(0.0, "no HTML to inspect")
        html = snapshot.html
        signals = {
            "title": bool(htmlutils.title(html)),
            "meta description": htmlutils.has_meta_description(html),
            "h1": htmlutils.has_h1(html),
            "lang": bool(htmlutils.lang(html)),
        }
        present = sum(signals.values())
        missing = [k for k, ok in signals.items() if not ok]
        details = "all basics present" if not missing else f"missing: {', '.join(missing)}"
        return self._result(present / len(signals), details)
