from __future__ import annotations

from sitefinder.analyzer.audit import WebsiteAuditor
from sitefinder.analyzer.checkers import (
    AccessibilityChecker,
    BookingChecker,
    ContactInfoChecker,
    MobileFriendlinessChecker,
    PerformanceChecker,
    SeoChecker,
    SslChecker,
    default_checkers,
)
from sitefinder.analyzer.models import SiteSnapshot
from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Provenance, WebPresence

GOOD_HTML = """
<html lang="de"><head><title>Zahnarzt Huber Wien</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Moderne Zahnarztpraxis in Wien">
</head><body><h1>Willkommen</h1>
<a href="tel:+4315230000">Anrufen</a> <a href="/impressum">Impressum</a>
<a href="https://calendly.com/huber">Termin buchen</a>
<img src="a.jpg" alt="Praxis"><img src="b.jpg" alt="Team">
</body></html>
"""

POOR_HTML = "<html><head><title></title></head><body>Welcome</body></html>"


def _snap(html=None, https=True, reachable=True, status=200, ms=400.0):
    return SiteSnapshot(
        requested_url="http://x.at",
        final_url=("https://x.at" if https else "http://x.at"),
        reachable=reachable,
        status_code=status,
        is_https=https,
        elapsed_ms=ms,
        html=html,
    )


def _biz(website="https://x.at"):
    return Business(
        name="X",
        category="dentist",
        web_presence=WebPresence(status=WebsiteStatus.HAS_SITE, effective_website=website),
        provenance=Provenance(discovered_by=SourceName.OSM),
    )


# ---- individual checkers ----

def test_ssl_checker():
    assert SslChecker().check(_snap(GOOD_HTML, https=True)).score == 1.0
    assert SslChecker().check(_snap(GOOD_HTML, https=False)).score == 0.0


def test_mobile_checker():
    assert MobileFriendlinessChecker().check(_snap(GOOD_HTML)).score == 1.0
    assert MobileFriendlinessChecker().check(_snap(POOR_HTML)).score == 0.0


def test_seo_checker_counts_signals():
    assert SeoChecker().check(_snap(GOOD_HTML)).score == 1.0
    assert SeoChecker().check(_snap(POOR_HTML)).score < 0.5


def test_contact_and_booking():
    assert ContactInfoChecker().check(_snap(GOOD_HTML)).score == 1.0
    assert BookingChecker().check(_snap(GOOD_HTML)).score == 1.0
    assert BookingChecker().check(_snap(POOR_HTML)).score == 0.0


def test_performance_thresholds():
    assert PerformanceChecker().check(_snap(GOOD_HTML, ms=200)).score == 1.0
    assert PerformanceChecker().check(_snap(GOOD_HTML, ms=5000)).score == 0.1


def test_accessibility_alt_and_lang():
    assert AccessibilityChecker().check(_snap(GOOD_HTML)).score == 1.0
    assert AccessibilityChecker().check(_snap(POOR_HTML)).score == 0.5  # no images, no lang


# ---- auditor aggregation ----

def test_auditor_good_site_scores_high():
    auditor = WebsiteAuditor(fetcher=lambda url: _snap(GOOD_HTML))
    report = auditor.audit(_biz())
    assert report.reachable is True
    assert report.audit_score >= 90
    assert len(report.checks) == len(default_checkers())


def test_auditor_poor_site_scores_low():
    auditor = WebsiteAuditor(fetcher=lambda url: _snap(POOR_HTML, https=False))
    report = auditor.audit(_biz())
    assert report.audit_score < 40


def test_auditor_no_website_is_zero_no_fetch():
    calls = []
    auditor = WebsiteAuditor(fetcher=lambda url: calls.append(url) or _snap(GOOD_HTML))
    report = auditor.audit(_biz(website=None))
    assert report.audit_score == 0.0
    assert report.url is None
    assert calls == []  # never fetched


def test_auditor_unreachable_site_low_score():
    auditor = WebsiteAuditor(fetcher=lambda url: _snap(html=None, reachable=False))
    report = auditor.audit(_biz())
    assert report.reachable is False
    assert report.audit_score < 30
