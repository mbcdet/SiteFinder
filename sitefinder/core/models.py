from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from sitefinder.core.enums import SourceName, WebsiteMatch, WebsiteStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Location(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    street: str | None = None
    postal_code: str | None = None  # PLZ — district key in Vienna (1070 -> District 7)
    city: str | None = None
    country_code: str = "AT"
    district: int | None = None


class Contact(BaseModel):
    phone: str | None = None
    email: str | None = None  # collected sparingly (GDPR)


class Rating(BaseModel):
    score: float | None = None
    review_count: int | None = None
    source: SourceName


class WebPresence(BaseModel):
    """Web presence with provider provenance preserved.

    Raw provider-reported websites are kept independently (`website_osm`, `website_google`);
    `effective_website` is the social-aware site the audit should use; `website_match` records
    how the two providers compare. Phase 2 consumes this normalized shape regardless of whether
    Google enrichment ran."""

    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    website_osm: str | None = None
    website_google: str | None = None
    effective_website: str | None = None  # derived by the checker (social links excluded)
    website_match: WebsiteMatch = WebsiteMatch.NONE
    social_urls: list[str] = Field(default_factory=list)
    checked_at: datetime | None = None


class Provenance(BaseModel):
    discovered_by: SourceName
    enriched_by: list[SourceName] = Field(default_factory=list)
    source_ids: dict[str, str] = Field(default_factory=dict)  # {"osm": "node/123"}
    first_seen: datetime = Field(default_factory=utcnow)
    last_updated: datetime = Field(default_factory=utcnow)
    last_enriched: datetime | None = None


class Business(BaseModel):
    """Central aggregate; the only type the pipeline and repository pass around."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: str
    location: Location = Field(default_factory=Location)
    contact: Contact = Field(default_factory=Contact)
    rating: Rating | None = None
    web_presence: WebPresence = Field(default_factory=WebPresence)
    provenance: Provenance
    is_deleted: bool = False


class DiscoveryQuery(BaseModel):
    """Resolved query handed to a DataSource (region config already applied)."""

    category: str
    city: str
    district: int
    country_code: str = "AT"
    osm_area: str = ""  # Overpass area name, e.g. "Wien" (differs from display city)
    district_area: str = ""  # district admin-boundary name, e.g. "Neubau" (preferred search)
    osm_tags: list[str] = Field(default_factory=list)  # e.g. ["amenity=dentist"]
    postal_codes: list[str] = Field(default_factory=list)  # district filter (fallback strategy)
    limit: int | None = None


class QueryCriteria(BaseModel):
    category: str | None = None
    district: int | None = None
    website_status: WebsiteStatus | None = None
    include_deleted: bool = False


class RunReport(BaseModel):
    """Structured summary of one pipeline run. Built by the pipeline, rendered by Reporter."""

    run_id: str
    category: str
    district: int
    source: SourceName
    enricher: SourceName | None = None

    collected: int = 0
    duplicates_removed: int = 0
    persisted: int = 0

    no_website: int = 0
    social_only: int = 0
    has_website: int = 0

    enriched: int = 0  # pipeline health, NOT lead count
    not_enriched: int = 0

    potential_leads: int = 0  # = no_website + social_only

    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    duration_seconds: float = 0.0
