from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from sitefinder.collector.osm_source import OSMDataSource
from sitefinder.config.region import RegionConfig
from sitefinder.config.settings import Settings
from sitefinder.core.models import DiscoveryQuery, QueryCriteria
from sitefinder.database.repository import SqliteRepository
from sitefinder.exporters.csv_exporter import CsvExporter
from sitefinder.infra.logging import configure_logging, get_logger
from sitefinder.infra.rate_limit import RateLimiter
from sitefinder.pipeline import Pipeline
from sitefinder.reports.validation import ValidationReporter
from sitefinder.website_checker.presence import PresenceChecker

app = typer.Typer(
    add_completion=False,
    help="SiteFinder — find Vienna businesses with no or poor website.",
)
log = get_logger("sitefinder.cli")


def _build_enricher(enrich: str | None, settings: Settings):
    if not enrich:
        return None
    if enrich.lower() == "places":
        from sitefinder.enricher.places_enricher import GooglePlacesEnricher

        if not settings.google_places_api_key:
            raise typer.BadParameter(
                "Places enrichment requires SITEFINDER_GOOGLE_PLACES_API_KEY in the environment."
            )
        return GooglePlacesEnricher(
            api_key=settings.google_places_api_key,
            timeout=settings.request_timeout,
            rate_limiter=RateLimiter(0.1),
        )
    raise typer.BadParameter(f"Unknown enrichment provider: {enrich!r}")


@app.command()
def run(
    district: int = typer.Option(..., "--district", "-d", help="Vienna district (1-23)"),
    category: str = typer.Option(..., "--category", "-c", help="Business category"),
    export: Optional[Path] = typer.Option(None, "--export", help="CSV output path"),
    enrich: Optional[str] = typer.Option(None, "--enrich", help="Enrichment provider: 'places'"),
    db: Optional[Path] = typer.Option(None, "--db", help="SQLite DB path (overrides default)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    """Discover, classify, persist and export leads for one category + district."""
    configure_logging(logging.DEBUG if verbose else logging.INFO)
    settings = Settings()
    if db is not None:
        settings.db_path = db
    region = RegionConfig.load(settings.region_file)

    try:
        query = DiscoveryQuery(
            category=category,
            city=region.city,
            district=district,
            country_code=region.country_code,
            osm_area=region.overpass_area,
            osm_tags=region.osm_tags(category),
            postal_codes=region.postal_codes(district),
        )
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    source = OSMDataSource(
        region,
        settings.overpass_url,
        settings.request_timeout,
        RateLimiter(settings.overpass_min_interval),
    )
    enricher = _build_enricher(enrich, settings)

    with SqliteRepository(settings.db_path) as repo:
        pipeline = Pipeline(source, PresenceChecker(), repo, enricher, settings.freshness_days)
        report = pipeline.run(query)
        businesses = repo.find(QueryCriteria(category=category, district=district))

    csv_path = export or Path(f"leads_d{district}_{category}.csv")
    CsvExporter().export(businesses, csv_path)

    report_path = csv_path.with_name(f"report_d{district}_{category}.txt")
    text = ValidationReporter().render(report, report_path)
    typer.echo("\n" + text + "\n")
    typer.echo(f"CSV:    {csv_path}")
    typer.echo(f"Report: {report_path}")


@app.command()
def categories() -> None:
    """List configured business categories."""
    region = RegionConfig.load(Settings().region_file)
    for name in region.category_names():
        typer.echo(name)


if __name__ == "__main__":
    app()
