from __future__ import annotations

import json
from pathlib import Path

import pytest

from sitefinder.config.region import RegionConfig
from sitefinder.config.settings import DEFAULT_REGION

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def region() -> RegionConfig:
    return RegionConfig.load(DEFAULT_REGION)


@pytest.fixture
def overpass_dentist_1070() -> dict:
    return json.loads((FIXTURES / "overpass_dentist_1070.json").read_text(encoding="utf-8"))
