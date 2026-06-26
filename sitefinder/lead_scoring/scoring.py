from __future__ import annotations

from sitefinder.analyzer.models import AuditReport
from sitefinder.core.enums import WebsiteStatus
from sitefinder.core.models import Business
from sitefinder.lead_scoring.models import LeadScore

# Tunable, transparent, rules-based — no ML. A good lead = poor/absent web presence,
# optionally weighted up if the business is clearly established (reviews).
_BASE_NO_WEBSITE = 90.0
_BASE_SOCIAL_ONLY = 80.0
_HAS_SITE_FACTOR = 0.7  # opportunity from a weak existing site
_MAX_REPUTATION_BONUS = 10.0


def _band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def score_lead(business: Business, audit: AuditReport) -> LeadScore:
    status = business.web_presence.status
    reasons: list[str] = []

    if status is WebsiteStatus.NONE:
        base = _BASE_NO_WEBSITE
        reasons.append("No website found")
    elif status is WebsiteStatus.SOCIAL_ONLY:
        base = _BASE_SOCIAL_ONLY
        reasons.append("Social media only, no real website")
    elif status is WebsiteStatus.HAS_SITE:
        base = _HAS_SITE_FACTOR * (100.0 - audit.audit_score)
        reasons.append(f"Existing website scored {audit.audit_score:.0f}/100")
        if not audit.reachable:
            reasons.append("Website unreachable")
        weak = [c.name for c in audit.checks if c.applicable and c.score < 0.5]
        if weak:
            reasons.append("Weak areas: " + ", ".join(weak))
    else:
        base = 50.0
        reasons.append("Web presence unknown")

    bonus = 0.0
    rating = business.rating
    if rating and rating.review_count:
        bonus = min(_MAX_REPUTATION_BONUS, rating.review_count / 20.0)
        reasons.append(f"Established ({rating.review_count} reviews)")

    score = round(max(0.0, min(100.0, base + bonus)), 1)
    return LeadScore(business_id=business.id, score=score, band=_band(score), reasons=reasons)
