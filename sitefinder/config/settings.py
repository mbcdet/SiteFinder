from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGION = PACKAGE_ROOT / "config" / "regions" / "vienna.yaml"


class Settings(BaseSettings):
    """Environment-backed application settings (prefix SITEFINDER_)."""

    model_config = SettingsConfigDict(
        env_prefix="SITEFINDER_", env_file=".env", extra="ignore"
    )

    region_file: Path = DEFAULT_REGION
    db_path: Path = Path("sitefinder.db")

    request_timeout: float = 30.0
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    overpass_min_interval: float = 1.0  # seconds between Overpass requests (politeness)

    freshness_days: int = 30  # skip re-enrichment within this window

    google_places_api_key: str | None = None
