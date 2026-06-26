from __future__ import annotations

from sitefinder.core.enums import SourceName, WebsiteMatch, WebsiteStatus
from sitefinder.core.models import Business, Provenance, WebPresence
from sitefinder.website_checker.presence import PresenceChecker


def _biz(
    website_osm: str | None = None,
    website_google: str | None = None,
    social: list[str] | None = None,
) -> Business:
    return Business(
        name="Test",
        category="dentist",
        web_presence=WebPresence(
            website_osm=website_osm, website_google=website_google, social_urls=social or []
        ),
        provenance=Provenance(discovered_by=SourceName.OSM),
    )


def test_has_site():
    wp = PresenceChecker().classify(_biz(website_osm="https://example.at"))
    assert wp.status is WebsiteStatus.HAS_SITE
    assert wp.effective_website == "https://example.at"
    assert wp.website_match is WebsiteMatch.OSM_ONLY
    assert wp.checked_at is not None


def test_social_only_from_tag():
    wp = PresenceChecker().classify(_biz(social=["https://facebook.com/x"]))
    assert wp.status is WebsiteStatus.SOCIAL_ONLY


def test_website_pointing_to_social_is_reclassified():
    wp = PresenceChecker().classify(_biz(website_osm="https://www.facebook.com/laecheln"))
    assert wp.status is WebsiteStatus.SOCIAL_ONLY
    assert wp.effective_website is None
    assert wp.website_osm == "https://www.facebook.com/laecheln"  # raw provenance preserved
    assert "https://www.facebook.com/laecheln" in wp.social_urls


def test_match_status_when_both_agree():
    wp = PresenceChecker().classify(
        _biz(website_osm="http://huber.at", website_google="https://www.huber.at/")
    )
    assert wp.website_match is WebsiteMatch.MATCH


def test_google_only_status():
    wp = PresenceChecker().classify(_biz(website_google="https://only-google.at"))
    assert wp.status is WebsiteStatus.HAS_SITE
    assert wp.website_match is WebsiteMatch.GOOGLE_ONLY
    assert wp.effective_website == "https://only-google.at"


def test_none():
    wp = PresenceChecker().classify(_biz())
    assert wp.status is WebsiteStatus.NONE
    assert wp.website_match is WebsiteMatch.NONE
