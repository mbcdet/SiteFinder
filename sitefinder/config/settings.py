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

    freshness_days: int = 30  # cache window: skip re-enrichment within this many days

    google_places_api_key: str | None = None
    places_min_interval: float = 0.1  # seconds between Places requests
    enrichment_cost_per_call: float = 0.017  # for the pre-run cost estimate (USD)
    enrichment_seconds_per_call: float = 0.8  # for the pre-run time estimate

    audit_timeout: float = 15.0  # per-site fetch timeout for the website audit
