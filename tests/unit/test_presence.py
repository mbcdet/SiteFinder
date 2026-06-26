from __future__ import annotations

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Provenance, WebPresence
from sitefinder.website_checker.presence import PresenceChecker


def _biz(website: str | None = None, social: list[str] | None = None) -> Business:
    return Business(
        name="Test",
        category="dentist",
        web_presence=WebPresence(website_url=website, social_urls=social or []),
        provenance=Provenance(discovered_by=SourceName.OSM),
    )


def test_has_site():
    wp = PresenceChecker().classify(_biz(website="https://example.at"))
    assert wp.status is WebsiteStatus.HAS_SITE
    assert wp.checked_at is not None


def test_social_only_from_tag():
    wp = PresenceChecker().classify(_biz(social=["https://facebook.com/x"]))
    assert wp.status is WebsiteStatus.SOCIAL_ONLY


def test_website_pointing_to_social_is_reclassified():
    wp = PresenceChecker().classify(_biz(website="https://www.facebook.com/laecheln"))
    assert wp.status is WebsiteStatus.SOCIAL_ONLY
    assert wp.website_url is None
    assert wp.social_urls == ["https://www.facebook.com/laecheln"]


def test_none():
    wp = PresenceChecker().classify(_biz())
    assert wp.status is WebsiteStatus.NONE
