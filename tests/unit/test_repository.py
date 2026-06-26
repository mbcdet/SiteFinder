from __future__ import annotations

from sitefinder.core.enums import SourceName, WebsiteStatus
from sitefinder.core.models import (
    Business,
    Location,
    Provenance,
    QueryCriteria,
    RunReport,
    WebPresence,
)
from sitefinder.database.repository import SqliteRepository


def _biz(name="A", osm="node/1", status=WebsiteStatus.NONE, postal="1070") -> Business:
    return Business(
        name=name,
        category="dentist",
        location=Location(district=7, postal_code=postal),
        web_presence=WebPresence(status=status),
        provenance=Provenance(discovered_by=SourceName.OSM, source_ids={"osm": osm}),
    )


def test_upsert_get_roundtrip():
    repo = SqliteRepository(":memory:")
    b = _biz()
    repo.upsert(b)
    got = repo.get(b.id)
    assert got is not None
    assert got.name == "A"
    assert got.location.district == 7
    assert got.web_presence.status is WebsiteStatus.NONE


def test_upsert_idempotent_by_osm_id():
    repo = SqliteRepository(":memory:")
    first = _biz()
    repo.upsert(first)
    first_id = first.id
    first_seen = repo.get(first_id).provenance.first_seen

    second = _biz()  # fresh uuid, same osm id -> should update, not duplicate
    repo.upsert(second)

    assert len(repo.find(QueryCriteria())) == 1
    assert second.id == first_id
    assert repo.get(first_id).provenance.first_seen == first_seen


def test_find_filters_status_and_soft_delete():
    repo = SqliteRepository(":memory:")
    a = _biz(name="A", osm="node/1", status=WebsiteStatus.NONE)
    b = _biz(name="B", osm="node/2", status=WebsiteStatus.HAS_SITE)
    repo.upsert(a)
    repo.upsert(b)

    none_only = repo.find(QueryCriteria(website_status=WebsiteStatus.NONE))
    assert [x.name for x in none_only] == ["A"]

    repo.soft_delete(a.id)
    remaining = repo.find(QueryCriteria())
    assert [x.name for x in remaining] == ["B"]
    assert len(repo.find(QueryCriteria(include_deleted=True))) == 2


def test_save_report():
    repo = SqliteRepository(":memory:")
    repo.save_report(RunReport(run_id="r1", category="dentist", district=7, source=SourceName.OSM))
    row = repo._conn.execute("SELECT data FROM run_reports WHERE run_id='r1'").fetchone()
    assert row is not None
