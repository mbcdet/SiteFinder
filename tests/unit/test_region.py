from __future__ import annotations

import pytest

from sitefinder.config.region import RegionConfig
from sitefinder.config.settings import DEFAULT_REGION


@pytest.fixture(scope="module")
def region() -> RegionConfig:
    return RegionConfig.load(DEFAULT_REGION)


def test_postal_codes_for_district(region):
    assert region.postal_codes(7) == ["1070"]
    assert region.postal_codes(23) == ["1230"]


def test_district_reverse_lookup(region):
    assert region.district_for_postal("1070") == 7
    assert region.district_for_postal("9999") is None
    assert region.district_for_postal(None) is None


def test_osm_tags_known_and_unknown(region):
    assert "amenity=dentist" in region.osm_tags("dentist")
    with pytest.raises(KeyError):
        region.osm_tags("nonexistent")


def test_unknown_district_raises(region):
    with pytest.raises(KeyError):
        region.postal_codes(99)
