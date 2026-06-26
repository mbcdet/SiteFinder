CREATE TABLE IF NOT EXISTS businesses (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    category       TEXT NOT NULL,
    district       INTEGER,
    postal_code    TEXT,
    website_status TEXT NOT NULL,
    osm_id         TEXT,
    is_deleted     INTEGER NOT NULL DEFAULT 0,
    last_updated   TEXT NOT NULL,
    data           TEXT NOT NULL   -- full Business JSON (round-trip fidelity)
);

CREATE INDEX IF NOT EXISTS idx_businesses_osm_id ON businesses(osm_id);
CREATE INDEX IF NOT EXISTS idx_businesses_filter
    ON businesses(category, district, website_status, is_deleted);

CREATE TABLE IF NOT EXISTS run_reports (
    run_id       TEXT PRIMARY KEY,
    category     TEXT NOT NULL,
    district     INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    data         TEXT NOT NULL   -- full RunReport JSON
);
