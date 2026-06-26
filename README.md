# SiteFinder

Phase 1 MVP — finds local businesses in Vienna that have **no website** or only a
**social-media presence**, so you can approach them in person and offer web-development
services. See [ARCHITECTURE.md](ARCHITECTURE.md) and [ROADMAP_PHASE1.md](ROADMAP_PHASE1.md).

## Install (local)

Requires Python 3.12+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
# List configured categories
sitefinder categories

# Discover dentists in District 7 (OSM only, free)
sitefinder run --district 7 --category dentist

# Custom output path
sitefinder run -d 7 -c hair_salon --export leads_07_hair.csv
```

Each run writes two files next to the CSV:

* `leads_d<district>_<category>.csv` — the leads (all stored businesses for that segment)
* `report_d<district>_<category>.txt` — the validation report

and stores everything in SQLite (`sitefinder.db` by default; override with `--db`).

### Optional Google Places enrichment

Adds rating, review count, and authoritative website for the discovered businesses.
**Off by default** — costs money beyond Google's free tier, so enable deliberately.

```bash
export SITEFINDER_GOOGLE_PLACES_API_KEY=your_key
sitefinder run -d 7 -c dentist --enrich places
```

Enrichment runs only on discovered survivors and reuses fresh cached results
(`SITEFINDER_FRESHNESS_DAYS`, default 30) to limit API calls.

## Configuration

Settings come from the environment (prefix `SITEFINDER_`) or a `.env` file — see
`.env.example`. Categories and districts are data, not code: edit
`sitefinder/config/regions/vienna.yaml` to add categories or (later) new cities.

## Testing

```bash
pytest
```

The suite covers models, region config, OSM mapping, dedup, presence classification,
repository (incl. idempotent upsert and soft-delete), CSV export, the pipeline report
assembly, and the Places enricher — all against fixtures, no network required.

## Notes on verification

The OSM/Places integrations were validated end-to-end against representative
OSM-response fixtures (the live calls require network access). To validate against live
Vienna data, simply run the commands above — they hit the public Overpass API directly.
