from __future__ import annotations

from urllib.parse import urlparse

from sitefinder.core.enums import WebsiteStatus
from sitefinder.core.interfaces import WebsiteChecker
from sitefinder.core.models import Business, WebPresence, utcnow

# A "website" that is actually a social profile is a SOCIAL_ONLY lead, not HAS_SITE.
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


class PresenceChecker(WebsiteChecker):
    """Phase 1: classify web presence from collected URLs only (no network fetch).

    Quality auditing of real sites (speed, mobile, SEO) is Phase 2; HAS_SITE here means
    only that a non-social website URL exists.
    """

    def classify(self, business: Business) -> WebPresence:
        current = business.web_presence
        website = current.website_url
        social = list(current.social_urls)

        if website and _is_social(website):
            social.append(website)
            website = None

        if website:
            status = WebsiteStatus.HAS_SITE
        elif social:
            status = WebsiteStatus.SOCIAL_ONLY
        else:
            status = WebsiteStatus.NONE

        return WebPresence(
            status=status,
            website_url=website,
            social_urls=social,
            checked_at=utcnow(),
        )
