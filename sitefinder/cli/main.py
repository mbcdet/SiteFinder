from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from sitefinder.analyzer.audit import WebsiteAuditor
from sitefinder.audit_pipeline import ScoredLead, run_audit_pipeline
from sitefinder.collector.osm_source import OSMDataSource
from sitefinder.config.region import RegionConfig
from sitefinder.config.settings import Settings
from sitefinder.core.models import DiscoveryQuery, QueryCriteria
from sitefinder.database.repository import SqliteRepository
from sitefinder.enricher.places_enricher import GooglePlacesEnricher
from sitefinder.enricher.runner import plan_enrichment, run_enrichment
from sitefinder.exporters.csv_exporter import CsvExporter
from sitefinder.infra.logging import configure_logging, get_logger
from sitefinder.infra.rate_limit import RateLimiter
from sitefinder.pipeline import Pipeline
from sitefinder.reports.audit_report import AuditReporter
from sitefinder.reports.final_report import FinalReporter
from sitefinder.reports.validation import ValidationReporter
from sitefinder.website_checker.presence import PresenceChecker

app = typer.Typer(
    add_completion=False,
    help="SiteFinder — find Vienna businesses with no or poor website.",
)
log = get_logger("sitefinder.cli")

_RECOMMENDED = 20


def _segment_dir(category: str, district: int) -> Path:
    return Path("results") / category / f"district_{district:02d}"


def _parse_count(raw: str, total: int) -> int:
    raw = raw.strip().lower()
    if raw in ("all", "*"):
        return total
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _places_enricher(settings: Settings) -> GooglePlacesEnricher:
    return GooglePlacesEnricher(
        api_key=settings.google_places_api_key or "",
        timeout=settings.request_timeout,
        rate_limiter=RateLimiter(settings.places_min_interval),
    )


@app.command()
def run(
    district: int = typer.Option(..., "--district", "-d", help="Vienna district (1-23)"),
    category: str = typer.Option(..., "--category", "-c", help="Business category"),
    audit: bool = typer.Option(True, "--audit/--no-audit", help="Run the website audit + scoring"),
    export: Optional[Path] = typer.Option(None, "--export", help="leads.csv output path"),
    db: Optional[Path] = typer.Option(None, "--db", help="SQLite DB path (overrides default)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    """Discover leads, audit their websites, score them, and write reports (free; no Google).

    Enrichment is a separate command — see `sitefinder enrich`.
    """
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
            district_area=region.district_name(district) or "",
            osm_tags=region.osm_tags(category),
            postal_codes=region.postal_codes(district),
        )
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    source = OSMDataSource(
        region, settings.overpass_url, settings.request_timeout,
        RateLimiter(settings.overpass_min_interval),
    )
    out_dir = export.parent if export is not None else _segment_dir(category, district)

    with SqliteRepository(settings.db_path) as repo:
        report = Pipeline(
            source, PresenceChecker(), repo, freshness_days=settings.freshness_days
        ).run(query)
        ValidationReporter().render(report, out_dir / "report.txt")
        leads_csv = export or out_dir / "leads.csv"

        if audit:
            leads = _run_audit(repo, settings, category, district, out_dir)
            CsvExporter().export_scored(leads, leads_csv)
        else:
            businesses = repo.find(QueryCriteria(category=category, district=district))
            CsvExporter().export(businesses, leads_csv)

    typer.echo(f"\nLeads: {report.persisted} | potential: {report.potential_leads}")
    typer.echo(f"Output: {out_dir}/")
    typer.echo("Tip: prioritize with Google ratings via  sitefinder enrich "
               f"-d {district} -c {category}")


@app.command()
def enrich(
    district: int = typer.Option(..., "--district", "-d", help="Vienna district (1-23)"),
    category: str = typer.Option(..., "--category", "-c", help="Business category"),
    top: Optional[int] = typer.Option(
        None, "--top", "-n", help="Enrich N leads (bypasses the interactive prompt)"
    ),
    assume_yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip prompts; enrich the recommended count"
    ),
    audit: bool = typer.Option(
        True, "--audit/--no-audit", help="Refresh audit + scoring after enriching"
    ),
    export: Optional[Path] = typer.Option(None, "--export", help="Enriched CSV output path"),
    db: Optional[Path] = typer.Option(None, "--db", help="SQLite DB path (overrides default)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    """Enrich stored leads with Google Places (interactive by default; never re-runs discovery).

    Manual use is interactive (asks how many, previews cost, confirms). Automated use stays
    non-interactive when `--top` or `--yes` is given.
    """
    configure_logging(logging.DEBUG if verbose else logging.INFO)
    settings = Settings()
    if db is not None:
        settings.db_path = db
    if not settings.google_places_api_key:
        raise typer.BadParameter("Enrichment requires SITEFINDER_GOOGLE_PLACES_API_KEY.")

    enricher = _places_enricher(settings)
    with SqliteRepository(settings.db_path) as repo:
        total = len(repo.find(QueryCriteria(category=category, district=district)))
        if total == 0:
            typer.echo(
                f"No stored leads for {category} in district {district}. "
                f"Run discovery first: sitefinder run -d {district} -c {category}"
            )
            raise typer.Exit(code=1)

        count = _resolve_count(enricher, settings, repo, category, district, total, top, assume_yes)
        if count <= 0:
            typer.echo("Cancelled — no API requests sent.")
            raise typer.Exit(code=0)

        result = run_enrichment(
            repo, enricher, PresenceChecker(), category, district, count, settings.freshness_days
        )
        out_dir = export.parent if export is not None else _segment_dir(category, district)
        enriched_csv = export or out_dir / "leads_enriched.csv"

        if audit:
            leads = _run_audit(repo, settings, category, district, out_dir)
            CsvExporter().export_scored(leads, enriched_csv, enriched=True)
        else:
            businesses = repo.find(QueryCriteria(category=category, district=district))
            CsvExporter().export(businesses, enriched_csv, enriched=True)

    typer.echo(
        f"Enriched {result.enriched} (cached {result.cached}, unsupported {result.unsupported})."
    )
    typer.echo(f"Output: {out_dir}/")


def _resolve_count(
    enricher: GooglePlacesEnricher,
    settings: Settings,
    repo: SqliteRepository,
    category: str,
    district: int,
    total: int,
    top: Optional[int],
    assume_yes: bool,
) -> int:
    """Decide how many leads to enrich. Flags bypass interaction; otherwise prompt + preview."""
    recommended = min(_RECOMMENDED, total)
    if top is not None:
        return top
    if assume_yes:
        return recommended
    if not sys.stdin.isatty():
        raise typer.BadParameter(
            "Non-interactive shell: pass --top N or --yes to enrich without prompts."
        )

    typer.echo(f"\n{total} potential leads found.")
    raw = typer.prompt(
        f'How many would you like to enrich?\nRecommended: {recommended}\n'
        f'Enter a number (or type "all")',
        default=str(recommended),
    )
    count = _parse_count(raw, total)
    if count <= 0:
        return 0

    plan = plan_enrichment(repo, enricher, category, district, count, settings.freshness_days)
    cost = plan.new_requests * settings.enrichment_cost_per_call
    seconds = plan.new_requests * settings.enrichment_seconds_per_call
    typer.echo("")
    typer.echo(f"Potential Leads : {plan.total}")
    typer.echo(f"Selected        : {plan.selected}")
    typer.echo(f"Cached          : {plan.cached}")
    typer.echo(f"New Requests    : {plan.new_requests}")
    typer.echo(f"Estimated Cost  : ~${cost:.2f}")
    typer.echo(f"Estimated Time  : ~{seconds:.0f} seconds")
    return count if typer.confirm("Continue?", default=True) else 0


def _run_audit(
    repo: SqliteRepository, settings: Settings, category: str, district: int, out_dir: Path
) -> list[ScoredLead]:
    """Audit + score the segment, write the detailed reports, and return the scored leads
    (so the caller can append the compact summary to the CSV)."""
    leads = run_audit_pipeline(
        repo, WebsiteAuditor(timeout=settings.audit_timeout), category, district
    )
    AuditReporter().render(leads, out_dir / "audit_report.txt")
    FinalReporter().render(leads, category, district, out_dir / "final_report.txt")
    return leads


@app.command()
def categories() -> None:
    """List configured business categories."""
    region = RegionConfig.load(Settings().region_file)
    for name in region.category_names():
        typer.echo(name)


if __name__ == "__main__":
    app()
