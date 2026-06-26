from __future__ import annotations

from sitefinder.collector.dedup import deduplicate
from sitefinder.collector.osm_source import element_to_business


def _businesses(region, payload):
    return [
        b
        for el in payload["elements"]
        if (b := element_to_business(el, "dentist", region)) is not None
    ]


def test_dedup_collapses_node_way_duplicate(region, overpass_dentist_1070):
    businesses = _businesses(region, overpass_dentist_1070)
    assert len(businesses) == 5
    unique, removed = deduplicate(businesses)
    assert removed == 1  # node/111 and way/666 are the same practice (name + postcode)
    assert len(unique) == 4
    names = [b.name for b in unique]
    assert names.count("Zahnarztpraxis Dr. Huber") == 1


def test_dedup_empty():
    unique, removed = deduplicate([])
    assert unique == [] and removed == 0
