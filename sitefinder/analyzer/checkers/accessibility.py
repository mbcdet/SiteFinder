from __future__ import annotations

from sitefinder.analyzer import htmlutils
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class AccessibilityChecker(Checker):
    """Practical a11y signals available from static HTML: a document lang and image alt text."""

    name = "accessibility"
    weight = 0.5

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.html:
            return self._result(0.0, "no HTML to inspect")
        html = snapshot.html
        has_lang = bool(htmlutils.lang(html))
        alt_ratio = htmlutils.img_alt_ratio(html)
        score = 0.5 * (1.0 if has_lang else 0.0) + 0.5 * alt_ratio
        details = f"lang={'yes' if has_lang else 'no'}, img alt coverage={alt_ratio:.0%}"
        return self._result(score, details)
