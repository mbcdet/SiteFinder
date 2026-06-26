from __future__ import annotations

from abc import ABC, abstractmethod

from sitefinder.analyzer.models import CheckResult, SiteSnapshot


class Checker(ABC):
    """A single-responsibility website check. Pure: analyzes a SiteSnapshot, no I/O.
    New checks plug in by implementing this interface and registering in default_checkers()."""

    name: str
    weight: float = 1.0

    @abstractmethod
    def check(self, snapshot: SiteSnapshot) -> CheckResult: ...

    def _result(self, score: float, details: str, applicable: bool = True) -> CheckResult:
        return CheckResult(
            name=self.name,
            score=max(0.0, min(1.0, score)),
            weight=self.weight,
            applicable=applicable,
            details=details,
        )
