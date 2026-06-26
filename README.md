# SiteFinder

Finds local businesses in Vienna that have **no website**, only a **social-media presence**,
or an **outdated/low-quality website**, then ranks them as web-development prospects so you can
approach the best ones in person. Discovery is free (OpenStreetMap); Google Places enrichment
and the website audit add prioritization. See [ARCHITECTURE.md](ARCHITECTURE.md).

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

# Custom output path (report.txt is written alongside)
sitefinder run -d 7 -c hair_salon --export some/dir/leads.csv
```

`run` does the free workflow: **discovery → website audit → lead scoring → reports.** Enrichment
is a **separate command** (`sitefinder enrich`), never folded into `run`. Each run writes an
organized, non-overwriting tree:

```
results/<category>/district_<NN>/
    leads.csv            # leads + compact audit summary (sortable in Excel)
    leads_enriched.csv   # only if Google enrichment ran (adds Google website/match/Place ID)
    report.txt           # discovery validation report
    audit_report.txt     # detailed per-site checker breakdown
    final_report.txt     # ranked leads by web-dev prospect score
```

When the audit runs, `leads.csv` gains four sortable columns — **Audit Score** (`N/A` for
businesses with no website), **Lead Score**, **Priority** (High/Medium/Low), and **Weak Areas**
(e.g. `performance, accessibility`). The full per-check explanations stay in `audit_report.txt`.

Useful flags: `--no-audit`, `--export`, `--db`, `-v`.
Everything is also stored in SQLite (`sitefinder.db` by default; override with `--db`).

### Run a matrix of categories x districts

```bash
scripts/run_matrix.sh "dentist hair_salon restaurant cafe barber physiotherapist" "1 6 7 8 15"
```

### Optional Google Places enrichment

Adds Google rating, review count, Maps URL and Place ID to **prioritize** which leads to visit.
**Optional and off by default** — it costs money beyond Google's free tier.

Enrichment is its own command — `sitefinder enrich`. **Manual use is interactive**; it reports how
many leads were found, recommends a count, then shows a cost/time preview and asks for confirmation
before sending any request:

```bash
export SITEFINDER_GOOGLE_PLACES_API_KEY=your_key
sitefinder enrich -d 5 -c hair_salon
```

```
35 potential leads found.
How many would you like to enrich?
Recommended: 20
Enter a number (or type "all"): 20

Potential Leads : 35
Selected        : 20
Cached          : 6
New Requests    : 14
Estimated Cost  : ~$0.24
Estimated Time  : ~11 seconds
Continue? [Y/n]
```

**Automated use stays non-interactive** when `--top` or `--yes` is given:

```bash
sitefinder enrich -d 5 -c hair_salon --top 20      # enrich exactly 20
sitefinder enrich -d 5 -c hair_salon --yes         # enrich the recommended count
```

Enrichment reads leads already stored by discovery (it never re-runs OSM), processes only the
**top N highest-priority** leads (no-website first, then social-only), records Google's website
**separately** from OSM's (`website_osm` vs `website_google`, plus a MATCH/OSM_ONLY/GOOGLE_ONLY/
DIFFERENT status), and writes `leads_enriched.csv` — `leads.csv` is never overwritten. `--top`
caps API usage; already-enriched leads are reused from cache within `SITEFINDER_FRESHNESS_DAYS`
(default 30), so the same business is never queried twice.

### Website audit & lead scoring (Phase 2)

The audit fetches each lead's website once and runs independent checkers (SSL, mobile,
performance, SEO, contact info, site health, accessibility, booking) over that snapshot,
producing `audit_report.txt`. Lead scoring then ranks businesses as web-dev prospects —
**no/poor website scores highest** — into `final_report.txt`. The audit runs identically whether
or not Google enrichment happened; Google is never required. Skip it with `--no-audit`.

## Configuration

Settings come from the environment (prefix `SITEFINDER_`) or a `.env` file — see
`.env.example`. Categories and districts are data, not code: edit
`sitefinder/config/regions/vienna.yaml` to add categories or (later) new cities.

## Testing

```bash
pytest
```

The suite covers models, region config, OSM mapping, dedup, presence classification (incl.
dual-website provenance), repository, CSV export, the pipeline, the Places enricher, every audit
checker, audit aggregation, and lead scoring — all against fixtures, no network required.

## Notes on verification

The OSM/Places integrations were validated end-to-end against representative
OSM-response fixtures (the live calls require network access). To validate against live
Vienna data, simply run the commands above — they hit the public Overpass API directly.
