from __future__ import annotations

from typing import Any

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Location, Provenance, WebPresence
from sitefinder.enricher.places_enricher import GooglePlacesEnricher
from sitefinder.infra.rate_limit import RateLimiter


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.last: dict[str, Any] | None = None

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> _FakeResponse:
        self.last = {"url": url, "headers": headers, "json": json}
        return _FakeResponse(self._payload)


def _biz(name="Zahnarzt Huber", lat=48.2, website=None) -> Business:
    return Business(
        name=name,
        category="dentist",
        location=Location(latitude=lat, longitude=16.3, postal_code="1070", city="Wien"),
        web_presence=WebPresence(website_osm=website),
        provenance=Provenance(discovered_by=SourceName.OSM, source_ids={"osm": "node/1"}),
    )


def _enricher(payload: dict) -> tuple[GooglePlacesEnricher, _FakeClient]:
    client = _FakeClient(payload)
    return GooglePlacesEnricher("KEY", rate_limiter=RateLimiter(0), client=client), client


def test_supports_requires_coords():
    e, _ = _enricher({})
    assert e.supports(_biz()) is True
    assert e.supports(_biz(lat=None)) is False


def test_enrich_populates_rating_website_placeid():
    payload = {
        "places": [
            {
                "id": "ChIJ123",
                "rating": 4.7,
                "userRatingCount": 53,
                "websiteUri": "https://huber.at",
            }
        ]
    }
    e, client = _enricher(payload)
    out = e.enrich(_biz())
    assert out.rating.score == 4.7
    assert out.rating.review_count == 53
    assert out.web_presence.website_google == "https://huber.at"
    assert out.provenance.source_ids["google_places"] == "ChIJ123"
    assert SourceName.GOOGLE_PLACES in out.provenance.enriched_by
    assert out.provenance.last_enriched is not None
    # field mask sent -> cost control
    assert "X-Goog-FieldMask" in client.last["headers"]


def test_enrich_no_match_is_noop():
    e, _ = _enricher({"places": []})
    out = e.enrich(_biz())
    assert out.rating is None
    assert "google_places" not in out.provenance.source_ids
