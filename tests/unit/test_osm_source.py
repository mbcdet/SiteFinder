from __future__ import annotations

from sitefinder.collector.osm_source import (
    OSMDataSource,
    build_overpass_query,
    element_to_business,
)
from sitefinder.core.models import DiscoveryQuery


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # noqa: D401
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, data: dict[str, str]) -> _FakeResponse:
        self.calls.append((url, data))
        return _FakeResponse(self._payload)


def _query() -> DiscoveryQuery:
    return DiscoveryQuery(
        category="dentist",
        city="Vienna",
        district=7,
        osm_area="Wien",
        osm_tags=["amenity=dentist", "healthcare=dentist"],
        postal_codes=["1070"],
    )


def test_build_overpass_query_structure():
    ql = build_overpass_query(_query())
    assert 'area["name"="Wien"]["admin_level"="4"]->.searchArea;' in ql
    assert 'nwr["amenity"="dentist"]["addr:postcode"="1070"](area.searchArea);' in ql
    assert 'nwr["healthcare"="dentist"]["addr:postcode"="1070"](area.searchArea);' in ql
    assert ql.strip().endswith("out center tags;")


def test_element_to_business_full_mapping(region, overpass_dentist_1070):
    huber = element_to_business(overpass_dentist_1070["elements"][0], "dentist", region)
    assert huber is not None
    assert huber.name == "Zahnarztpraxis Dr. Huber"
    assert huber.location.district == 7
    assert huber.location.postal_code == "1070"
    assert huber.location.street == "Mariahilfer Straße 10"
    assert huber.contact.phone == "+43 1 5230000"
    assert huber.web_presence.website_osm == "https://zahnarzt-huber.at"
    assert huber.provenance.source_ids["osm"] == "node/111"


def test_element_to_business_way_uses_center(region, overpass_dentist_1070):
    way = element_to_business(overpass_dentist_1070["elements"][3], "dentist", region)
    assert way is not None
    assert way.location.latitude == 48.2040
    assert way.provenance.source_ids["osm"] == "way/444"


def test_unnamed_element_skipped(region, overpass_dentist_1070):
    unnamed = overpass_dentist_1070["elements"][4]  # id 555, no name
    assert element_to_business(unnamed, "dentist", region) is None


def test_discover_with_injected_client(region, overpass_dentist_1070):
    client = _FakeClient(overpass_dentist_1070)
    source = OSMDataSource(region, "http://overpass.test", client=client)
    out = list(source.discover(_query()))
    assert len(out) == 5  # 6 elements, 1 unnamed skipped
    assert client.calls and client.calls[0][1]["data"].startswith("[out:json]")


def test_build_overpass_query_boundary_strategy():
    query = DiscoveryQuery(
        category="dentist",
        city="Vienna",
        district=7,
        district_area="Neubau",
        osm_tags=["amenity=dentist"],
        postal_codes=["1070"],
    )
    ql = build_overpass_query(query)
    assert (
        'area["boundary"="administrative"]["admin_level"="9"]["name"="Neubau"]->.searchArea;'
        in ql
    )
    assert 'nwr["amenity"="dentist"](area.searchArea);' in ql
    assert "addr:postcode" not in ql  # boundary search does not depend on the postcode tag


def test_default_district_used_when_postcode_missing(region):
    element = {
        "type": "node",
        "id": 1,
        "lat": 48.2,
        "lon": 16.3,
        "tags": {"amenity": "dentist", "name": "Praxis ohne PLZ"},
    }
    business = element_to_business(element, "dentist", region, default_district=7)
    assert business is not None
    # postcode backfilled from the searched district; district resolved either way
    assert business.location.postal_code == "1070"
    assert business.location.district == 7
