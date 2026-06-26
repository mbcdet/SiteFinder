from __future__ import annotations

from sitefinder.analyzer import htmlutils
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot

_CONTACT_WORDS = ("impressum", "kontakt", "contact", "anfahrt")


class ContactInfoChecker(Checker):
    """Looks for reachable contact info: tel:/mailto: links or contact/Impressum sections
    (Impressum is legally required for Austrian business sites, so its absence is notable)."""

    name = "contact_info"
    weight = 1.0

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.html:
            return self._result(0.0, "no HTML to inspect")
        html = snapshot.html
        has_link = htmlutils.has_tel_or_mailto(html)
        has_section = htmlutils.contains_any(html, _CONTACT_WORDS)
        if has_link and has_section:
            return self._result(1.0, "tel/mailto and contact section present")
        if has_link or has_section:
            return self._result(0.6, "partial contact info")
        return self._result(0.0, "no obvious contact info")
