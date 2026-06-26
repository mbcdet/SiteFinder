from __future__ import annotations

from sitefinder.analyzer.models import AuditReport, CheckResult
from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Provenance, Rating, WebPresence
from sitefinder.lead_scoring.scoring import score_lead


def _biz(status, rating=None):
    return Business(
        name="X",
        category="dentist",
        web_presence=WebPresence(status=status),
        rating=rating,
        provenance=Provenance(discovered_by=SourceName.OSM),
    )


def _audit(score, checks=None, reachable=True):
    return AuditReport(
        business_id="x", url="https://x.at", reachable=reachable, audit_score=score,
        checks=checks or [],
    )


def test_no_website_scores_highest():
    s = score_lead(_biz(WebsiteStatus.NONE), _audit(0.0))
    assert s.band == "high"
    assert s.score >= 90


def test_good_site_scores_low():
    s = score_lead(_biz(WebsiteStatus.HAS_SITE), _audit(95.0))
    assert s.band == "low"
    assert s.score < 20


def test_poor_site_scores_higher_than_good_site():
    poor = score_lead(_biz(WebsiteStatus.HAS_SITE), _audit(20.0))
    good = score_lead(_biz(WebsiteStatus.HAS_SITE), _audit(90.0))
    assert poor.score > good.score


def test_reputation_bonus_only_when_rating_present():
    rating = Rating(score=4.6, review_count=200, source=SourceName.GOOGLE_PLACES)
    with_rep = score_lead(_biz(WebsiteStatus.SOCIAL_ONLY, rating=rating), _audit(0.0))
    without = score_lead(_biz(WebsiteStatus.SOCIAL_ONLY), _audit(0.0))
    assert with_rep.score > without.score
    assert any("Established" in r for r in with_rep.reasons)


def test_weak_areas_listed():
    checks = [
        CheckResult(name="ssl", score=0.0, weight=1.5),
        CheckResult(name="mobile_friendly", score=0.0, weight=1.5),
        CheckResult(name="seo_basics", score=1.0, weight=1.0),
    ]
    s = score_lead(_biz(WebsiteStatus.HAS_SITE), _audit(40.0, checks=checks))
    assert any("ssl" in r and "mobile_friendly" in r for r in s.reasons)
