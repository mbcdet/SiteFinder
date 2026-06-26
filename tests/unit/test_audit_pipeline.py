from __future__ import annotations

from sitefinder.analyzer.audit import WebsiteAuditor
from sitefinder.analyzer.models import SiteSnapshot
from sitefinder.audit_pipeline import run_audit_pipeline
from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import Business, Location, Provenance, WebPresence
from sitefinder.database.repository import SqliteRepository
from sitefinder.reports.audit_report import AuditReporter
from sitefinder.reports.final_report import FinalReporter

GOOD = (
    '<html lang="de"><head><title>Good</title>'
    '<meta name="viewport" content="width=device-width">'
    '<meta name="description" content="desc that is reasonably long for the check to pass ok">'
    "</head><body><h1>Hi</h1>" + "x" * 600 + "</body></html>"
)


def _biz(name, status, website=None):
    return Business(
        name=name,
        category="dentist",
        location=Location(district=7, postal_code="1070", street="街 1"),
        web_presence=WebPresence(status=status, effective_website=website),
        provenance=Provenance(discovered_by=SourceName.OSM, source_ids={"osm": f"node/{name}"}),
    )


def _seed(repo):
    repo.upsert(_biz("NoSite", WebsiteStatus.NONE))
    repo.upsert(_biz("GoodSite", WebsiteStatus.HAS_SITE, "https://good.at"))


def _auditor():
    return WebsiteAuditor(
        fetcher=lambda url: SiteSnapshot(
            requested_url=url, final_url="https://good.at", reachable=True,
            status_code=200, is_https=True, elapsed_ms=300.0, html=GOOD,
        )
    )


def test_pipeline_ranks_no_website_above_good_site():
    repo = SqliteRepository(":memory:")
    _seed(repo)
    leads = run_audit_pipeline(repo, _auditor(), "dentist", 7)
    assert [lead.business.name for lead in leads] == ["NoSite", "GoodSite"]
    assert leads[0].score.band == "high"
    assert leads[-1].score.band == "low"


def test_reporters_render(tmp_path):
    repo = SqliteRepository(":memory:")
    _seed(repo)
    leads = run_audit_pipeline(repo, _auditor(), "dentist", 7)
    audit_txt = AuditReporter().render(leads, tmp_path / "audit_report.txt")
    final_txt = FinalReporter().render(leads, "dentist", 7, tmp_path / "final_report.txt")
    assert "WEBSITE AUDIT REPORT" in audit_txt
    assert "FINAL LEAD REPORT" in final_txt
    assert "NoSite" in final_txt
    assert (tmp_path / "audit_report.txt").exists()
    assert (tmp_path / "final_report.txt").exists()
