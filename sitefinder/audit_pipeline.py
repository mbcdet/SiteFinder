from __future__ import annotations

from dataclasses import dataclass

from sitefinder.analyzer.audit import WebsiteAuditor
from sitefinder.analyzer.models import AuditReport
from sitefinder.core.interfaces import Repository
from sitefinder.core.models import Business, QueryCriteria
from sitefinder.infra.logging import get_logger
from sitefinder.lead_scoring.models import LeadScore
from sitefinder.lead_scoring.scoring import score_lead

log = get_logger(__name__)


@dataclass
class ScoredLead:
    business: Business
    audit: AuditReport
    score: LeadScore


def run_audit_pipeline(
    repository: Repository,
    auditor: WebsiteAuditor,
    category: str,
    district: int,
) -> list[ScoredLead]:
    """Audit + score every stored lead of a segment, ranked best-prospect first.

    Operates on the normalized lead model from the repository — identical behavior whether or
    not Google enrichment ran. No-website leads are scored without any fetch."""
    businesses = repository.find(QueryCriteria(category=category, district=district))
    scored = [
        ScoredLead(business=b, audit=(audit := auditor.audit(b)), score=score_lead(b, audit))
        for b in businesses
    ]
    scored.sort(key=lambda s: s.score.score, reverse=True)
    log.info("Audited %d leads for %s district %d", len(scored), category, district)
    return scored
