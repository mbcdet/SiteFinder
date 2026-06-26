from __future__ import annotations

from urllib.parse import urlparse

from sitefinder.core.enums import WebsiteMatch, WebsiteStatus
from sitefinder.core.interfaces import WebsiteChecker
from sitefinder.core.models import Business, WebPresence, utcnow

# A "website" that is actually a social profile is a SOCIAL_ONLY signal, not a real site.
_SOCIAL_DOMAINS = (
    "facebook.",
    "fb.com",
    "fb.me",
    "instagram.",
    "tiktok.",
    "twitter.",
    "x.com",
    "linktr.ee",
    "linktree.",
)


def _is_social(url: str) -> bool:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower()
    return any(token in host for token in _SOCIAL_DOMAINS)


def _normalize(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return host + parsed.path.rstrip("/").lower()


def _derive_match(osm: str | None, google: str | None) -> WebsiteMatch:
    if osm and google:
        return WebsiteMatch.MATCH if _normalize(osm) == _normalize(google) else WebsiteMatch.DIFFERENT
    if osm:
        return WebsiteMatch.OSM_ONLY
    if google:
        return WebsiteMatch.GOOGLE_ONLY
    return WebsiteMatch.NONE


class PresenceChecker(WebsiteChecker):
    """Phase 1 classification from collected URLs (no network fetch). Quality auditing of live
    sites is Phase 2. Preserves raw provider websites; derives an effective site + match status."""

    def classify(self, business: Business) -> WebPresence:
        current = business.web_presence
        osm_raw = current.website_osm
        google_raw = current.website_google

        social = list(current.social_urls)
        for url in (osm_raw, google_raw):
            if url and _is_social(url):
                social.append(url)

        osm_site = osm_raw if (osm_raw and not _is_social(osm_raw)) else None
        google_site = google_raw if (google_raw and not _is_social(google_raw)) else None
        effective = osm_site or google_site

        if effective:
            status = WebsiteStatus.HAS_SITE
        elif social:
            status = WebsiteStatus.SOCIAL_ONLY
        else:
            status = WebsiteStatus.NONE

        return WebPresence(
            status=status,
            website_osm=osm_raw,  # raw provider data preserved
            website_google=google_raw,
            effective_website=effective,
            website_match=_derive_match(osm_raw, google_raw),
            social_urls=social,
            checked_at=utcnow(),
        )
