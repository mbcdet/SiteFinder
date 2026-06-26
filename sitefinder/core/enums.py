from __future__ import annotations

from enum import Enum


class SourceName(str, Enum):
    """Identifies a data source / enricher. Stored in provenance for ownership & dedup."""

    OSM = "osm"
    GOOGLE_PLACES = "google_places"
    HEROLD = "herold"  # future (Phase 1.5)
    FIRMENABC = "firmenabc"  # future (Phase 1.5)


class WebsiteStatus(str, Enum):
    """Web presence classification. SOCIAL_ONLY is a distinct, often high-value lead segment."""

    NONE = "none"
    SOCIAL_ONLY = "social_only"
    HAS_SITE = "has_site"
    UNKNOWN = "unknown"
