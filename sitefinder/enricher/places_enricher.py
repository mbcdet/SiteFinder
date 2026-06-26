from __future__ import annotations

from typing import Any, Protocol

from sitefinder.core.enums import SourceName
from sitefinder.core.interfaces import Enricher
from sitefinder.core.models import Business, Rating, utcnow
from sitefinder.infra import http
from sitefinder.infra.logging import get_logger
from sitefinder.infra.rate_limit import RateLimiter

log = get_logger(__name__)


class _HttpClient(Protocol):
    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> Any: ...


class GooglePlacesEnricher(Enricher):
    """Optional enrichment via Google Places API (New) Text Search.

    Uses a tight field mask (id, rating, review count, website) to stay in the cheapest
    SKU tier. Matches by name + postal/city. Off unless explicitly enabled by the CLI.
    """

    name = SourceName.GOOGLE_PLACES

    _ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
    _FIELD_MASK = (
        "places.id,places.displayName,places.rating,places.userRatingCount,places.websiteUri"
    )

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        rate_limiter: RateLimiter | None = None,
        client: _HttpClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._rate = rate_limiter or RateLimiter(0.1)
        self._client = client

    def supports(self, business: Business) -> bool:
        return bool(business.name) and business.location.latitude is not None

    def enrich(self, business: Business) -> Business:
        place = self._search(business)
        if not place:
            log.info("Places: no match for %r", business.name)
            return business

        business.rating = Rating(
            score=place.get("rating"),
            review_count=place.get("userRatingCount"),
            source=SourceName.GOOGLE_PLACES,
        )
        website = place.get("websiteUri")
        if website and not business.web_presence.website_url:
            business.web_presence.website_url = website
        if place_id := place.get("id"):
            business.provenance.source_ids["google_places"] = place_id
        if SourceName.GOOGLE_PLACES not in business.provenance.enriched_by:
            business.provenance.enriched_by.append(SourceName.GOOGLE_PLACES)
        business.provenance.last_enriched = utcnow()
        return business

    def _search(self, business: Business) -> dict[str, Any] | None:
        self._rate.wait()
        text_query = " ".join(
            part
            for part in (
                business.name,
                business.location.postal_code,
                business.location.city or "Wien",
            )
            if part
        )
        headers = {"X-Goog-Api-Key": self._api_key, "X-Goog-FieldMask": self._FIELD_MASK}
        body = {"textQuery": text_query, "maxResultCount": 1}

        client = self._client or http.build_client(self._timeout)
        owns_client = self._client is None
        try:
            resp = client.post(self._ENDPOINT, headers=headers, json=body)
            resp.raise_for_status()
            places = resp.json().get("places", [])
            return places[0] if places else None
        finally:
            if owns_client:
                client.close()
