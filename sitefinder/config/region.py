from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class CategoryConfig(BaseModel):
    osm_tags: list[str]


class RegionConfig(BaseModel):
    """Data-driven region definition. A new city is a new YAML file, not new code."""

    city: str
    country_code: str = "AT"
    osm_area: str = ""  # Overpass area name (defaults to city if empty)
    districts: dict[int, list[str]]  # district -> postal codes
    categories: dict[str, CategoryConfig]

    @property
    def overpass_area(self) -> str:
        return self.osm_area or self.city

    @classmethod
    def load(cls, path: Path | str) -> RegionConfig:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def postal_codes(self, district: int) -> list[str]:
        if district not in self.districts:
            raise KeyError(f"Unknown district: {district}")
        return self.districts[district]

    def osm_tags(self, category: str) -> list[str]:
        if category not in self.categories:
            raise KeyError(f"Unknown category: {category!r}. Known: {self.category_names()}")
        return self.categories[category].osm_tags

    def category_names(self) -> list[str]:
        return sorted(self.categories)

    def district_for_postal(self, postal_code: str | None) -> int | None:
        if not postal_code:
            return None
        for district, codes in self.districts.items():
            if postal_code in codes:
                return district
        return None
