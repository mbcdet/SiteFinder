from __future__ import annotations

from pydantic import BaseModel, Field


class SiteSnapshot(BaseModel):
    """Single fetch of a website. Checkers analyze this immutable snapshot with no further I/O."""

    requested_url: str
    final_url: str | None = None
    reachable: bool = False
    status_code: int | None = None
    is_https: bool = False
    elapsed_ms: float | None = None
    html: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class CheckResult(BaseModel):
    """Normalized output of a single checker. ``score`` is 0..1; ``weight`` is relative
    importance in the aggregate; non-applicable checks are excluded from the audit score."""

    name: str
    score: float
    weight: float = 1.0
    applicable: bool = True
    details: str = ""


class AuditReport(BaseModel):
    business_id: str
    url: str | None
    reachable: bool
    audit_score: float  # 0..100, weighted over applicable checks (higher = better site)
    checks: list[CheckResult] = Field(default_factory=list)
