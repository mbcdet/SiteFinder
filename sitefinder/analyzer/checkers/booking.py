from __future__ import annotations

from sitefinder.analyzer import htmlutils
from sitefinder.analyzer.checkers.base import Checker
from sitefinder.analyzer.models import CheckResult, SiteSnapshot

_BOOKING_SIGNS = (
    "termin",
    "reservier",
    "buchen",
    "booking",
    "appointment",
    "opentable",
    "resmio",
    "calendly",
    "quandoo",
    "treatwell",
)


class BookingChecker(Checker):
    """Online booking/appointment availability. Lower weight: relevant for some categories
    (salons, restaurants, physios) but not all, and its absence is an upsell opportunity."""

    name = "booking"
    weight = 0.5

    def check(self, snapshot: SiteSnapshot) -> CheckResult:
        if not snapshot.html:
            return self._result(0.0, "no HTML to inspect")
        if htmlutils.contains_any(snapshot.html, _BOOKING_SIGNS):
            return self._result(1.0, "online booking/appointment detected")
        return self._result(0.0, "no online booking detected")
