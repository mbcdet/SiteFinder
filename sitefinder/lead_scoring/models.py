from __future__ import annotations

from pydantic import BaseModel, Field


class LeadScore(BaseModel):
    """How good a web-development prospect a business is. Higher = better prospect
    (no/poor website + established) — the inverse of website quality."""

    business_id: str
    score: float  # 0..100
    band: str  # high / medium / low
    reasons: list[str] = Field(default_factory=list)
