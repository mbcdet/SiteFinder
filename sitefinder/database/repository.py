from __future__ import annotations

import sqlite3
from pathlib import Path

from sitefinder.core.interfaces import Repository
from sitefinder.core.models import Business, QueryCriteria, RunReport, utcnow

_SCHEMA = Path(__file__).with_name("schema.sql")


class SqliteRepository(Repository):
    """Repository over stdlib sqlite3. Queryable columns are mirrored alongside a JSON blob
    that preserves the full Business for lossless round-trips."""

    def __init__(self, db_path: Path | str) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA.read_text(encoding="utf-8"))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteRepository:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _osm_id(business: Business) -> str | None:
        return business.provenance.source_ids.get("osm")

    def upsert(self, business: Business) -> None:
        """Idempotent: if a matching record exists, its id and first_seen are preserved so
        repeated runs update rather than duplicate."""
        existing = self.find_match(business)
        if existing is not None:
            business.id = existing.id
            business.provenance.first_seen = existing.provenance.first_seen
        business.provenance.last_updated = utcnow()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO businesses
                (id, name, category, district, postal_code, website_status,
                 osm_id, is_deleted, last_updated, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business.id,
                business.name,
                business.category,
                business.location.district,
                business.location.postal_code,
                business.web_presence.status.value,
                self._osm_id(business),
                int(business.is_deleted),
                business.provenance.last_updated.isoformat(),
                business.model_dump_json(),
            ),
        )
        self._conn.commit()

    def get(self, business_id: str) -> Business | None:
        row = self._conn.execute(
            "SELECT data FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
        return Business.model_validate_json(row["data"]) if row else None

    def find_match(self, business: Business) -> Business | None:
        osm_id = self._osm_id(business)
        if osm_id:
            row = self._conn.execute(
                "SELECT data FROM businesses WHERE osm_id = ?", (osm_id,)
            ).fetchone()
            if row:
                return Business.model_validate_json(row["data"])
        row = self._conn.execute(
            "SELECT data FROM businesses "
            "WHERE lower(name) = lower(?) AND ifnull(postal_code,'') = ifnull(?,'')",
            (business.name, business.location.postal_code),
        ).fetchone()
        return Business.model_validate_json(row["data"]) if row else None

    def find(self, criteria: QueryCriteria) -> list[Business]:
        clauses: list[str] = []
        params: list[object] = []
        if not criteria.include_deleted:
            clauses.append("is_deleted = 0")
        if criteria.category:
            clauses.append("category = ?")
            params.append(criteria.category)
        if criteria.district is not None:
            clauses.append("district = ?")
            params.append(criteria.district)
        if criteria.website_status is not None:
            clauses.append("website_status = ?")
            params.append(criteria.website_status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT data FROM businesses{where} ORDER BY name", params
        ).fetchall()
        return [Business.model_validate_json(r["data"]) for r in rows]

    def soft_delete(self, business_id: str) -> None:
        self._conn.execute(
            "UPDATE businesses SET is_deleted = 1 WHERE id = ?", (business_id,)
        )
        self._conn.commit()

    def save_report(self, report: RunReport) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO run_reports "
            "(run_id, category, district, generated_at, data) VALUES (?, ?, ?, ?, ?)",
            (
                report.run_id,
                report.category,
                report.district,
                (report.finished_at or report.started_at).isoformat(),
                report.model_dump_json(),
            ),
        )
        self._conn.commit()
