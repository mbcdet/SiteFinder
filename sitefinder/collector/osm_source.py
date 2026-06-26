from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from sitefinder.config.region import RegionConfig
from sitefinder.core.enums import SourceName
from sitefinder.core.interfaces import DataSource
from sitefinder.core.models import (
    Business,
    Contact,
    DiscoveryQuery,
    Location,
    Provenance,
    WebPresence,
)
from sitefinder.infra import http
from sitefinder.infra.logging import get_logger
from sitefinder.infra.rate_limit import RateLimiter

log = get_logger(__name__)

_SOCIAL_TAG_KEYS = (
    "contact:facebook",
    "contact:instagram",
    "contact:tiktok",
    "facebook",
    "instagram",
)
_WEBSITE_TAG_KEYS = ("website", "contact:website", "url")


class _HttpClient(Protocol):
    def post(self, url: str, data: dict[str, str]) -> Any: ...


def _tag_pairs(osm_tags: list[str]) -> list[tuple[str, str]]:
    return [tuple(t.split("=", 1)) for t in osm_tags if "=" in t]  # type: ignore[misc]


def build_overpass_query(query: DiscoveryQuery, timeout: int = 60) -> str:
    """Pure function: build Overpass QL for a resolved DiscoveryQuery.

    Preferred strategy (``district_area`` set): search within the district administrative
    boundary (Bezirk, admin_level=9). This captures every business geographically in the
    district, including those lacking an ``addr:postcode`` tag — a major coverage gain over
    tag-based filtering.

    Fallback strategy: filter by the district's postal code(s) within the city area. Used only
    when no boundary name is configured; misses businesses without an ``addr:postcode`` tag.
    """
    pairs = _tag_pairs(query.osm_tags)

    if query.district_area:
        lines = [f'  nwr["{k}"="{v}"](area.searchArea);' for k, v in pairs]
        # boundary=administrative guards against non-boundary areas sharing the Bezirk name.
        area_decl = (
            f'area["boundary"="administrative"]["admin_level"="9"]'
            f'["name"="{query.district_area}"]->.searchArea;'
        )
    else:
        area = query.osm_area or query.city
        lines = [
            f'  nwr["{k}"="{v}"]["addr:postcode"="{plz}"](area.searchArea);'
            for k, v in pairs
            for plz in query.postal_codes
        ]
        area_decl = f'area["name"="{area}"]["admin_level"="4"]->.searchArea;'

    return (
        f"[out:json][timeout:{timeout}];\n"
        f"{area_decl}\n"
        f"(\n" + "\n".join(lines) + "\n);\n"
        f"out center tags;"
    )


def _coords(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def _street(tags: dict[str, str]) -> str | None:
    street = tags.get("addr:street")
    if not street:
        return None
    housenumber = tags.get("addr:housenumber")
    return f"{street} {housenumber}" if housenumber else street


def _first(tags: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if tags.get(key):
            return tags[key]
    return None


def element_to_business(
    element: dict[str, Any],
    category: str,
    region: RegionConfig,
    default_district: int | None = None,
) -> Business | None:
    """Map a single Overpass element to a Business. Returns None for unnamed elements
    (no name = not an actionable lead). Presence status is left UNKNOWN for the checker.

    ``default_district`` is the district we searched (boundary strategy); it is used when the
    element has no ``addr:postcode`` tag to derive the district from."""
    tags = element.get("tags", {})
    name = tags.get("name") or tags.get("brand")
    if not name:
        return None

    lat, lon = _coords(element)
    postal = tags.get("addr:postcode")
    if postal is None and default_district is not None:
        # Boundary search guarantees the district even when the POI lacks an addr:postcode tag.
        try:
            postal = region.postal_codes(default_district)[0]
        except (KeyError, IndexError):
            postal = None
    location = Location(
        latitude=lat,
        longitude=lon,
        street=_street(tags),
        postal_code=postal,
        city=tags.get("addr:city"),
        country_code=region.country_code,
        district=region.district_for_postal(postal) or default_district,
    )
    contact = Contact(
        phone=_first(tags, ("phone", "contact:phone")),
        email=_first(tags, ("email", "contact:email")),
    )
    web = WebPresence(
        website_osm=_first(tags, _WEBSITE_TAG_KEYS),
        social_urls=[tags[k] for k in _SOCIAL_TAG_KEYS if tags.get(k)],
    )
    source_id = f"{element.get('type')}/{element.get('id')}"
    provenance = Provenance(discovered_by=SourceName.OSM, source_ids={"osm": source_id})
    return Business(
        name=name,
        category=category,
        location=location,
        contact=contact,
        web_presence=web,
        provenance=provenance,
    )


class OSMDataSource(DataSource):
    """Discovers businesses from OpenStreetMap via the Overpass API."""

    name = SourceName.OSM

    def __init__(
        self,
        region: RegionConfig,
        overpass_url: str,
        timeout: float = 60.0,
        rate_limiter: RateLimiter | None = None,
        client: _HttpClient | None = None,
    ) -> None:
        self._region = region
        self._url = overpass_url
        self._timeout = timeout
        self._rate = rate_limiter or RateLimiter(1.0)
        self._client = client  # injectable for testing

    def discover(self, query: DiscoveryQuery) -> Iterable[Business]:
        ql = build_overpass_query(query, int(self._timeout))
        elements = self._fetch(ql)
        businesses = [
            b
            for el in elements
            if (b := element_to_business(el, query.category, self._region, query.district))
            is not None
        ]
        log.info(
            "OSM: %d named businesses (%d raw elements) for %s, district %d",
            len(businesses),
            len(elements),
            query.category,
            query.district,
        )
        return businesses

    def _fetch(self, ql: str) -> list[dict[str, Any]]:
        self._rate.wait()
        if self._client is not None:
            resp = self._client.post(self._url, data={"data": ql})
            resp.raise_for_status()
            return resp.json().get("elements", [])
        with http.build_client(self._timeout) as client:
            resp = client.post(self._url, data={"data": ql})
            resp.raise_for_status()
            return resp.json().get("elements", [])
