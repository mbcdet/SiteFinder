# SiteFinder — Phase 1 Roadmap (MVP = Technical Build + Business Validation)

> **Status:** Proposed → pending approval
> **Budget:** ~10–20 hours of build time, ~€0 operating cost
> **Companion:** see `ARCHITECTURE.md` for the frozen design

Phase 1 is deliberately the *whole skeleton, thinnest possible slice*. It must prove two things
at once: (a) the architecture holds together end to end, and (b) the leads it produces are good
enough to justify continuing. We decide what happens next from **real results, not assumptions**.

---

## 1. Phase 1 goal

> One command takes a **category** and a **Vienna district**, discovers businesses from OSM,
> de-duplicates them, classifies their web presence, persists them to SQLite, and exports a
> ranked-enough CSV of leads — at €0, in minutes.

Example:
```
sitefinder run --district 7 --category dentist --export leads_07_dentist.csv
```

Google Places enrichment is implemented but **off by default**; it can be switched on
(`--enrich places`) to add rating/reviews for the filtered survivors.

---

## 2. Success criteria (the validation gate)

Phase 1 succeeds — technically and as a business test — if, after running it across a few
categories (Dentist, Hair Salon, Restaurant) and a few districts:

**Technical**
- Runs end to end without manual intervention, idempotently (re-runs don't duplicate or re-pay).
- Produces a clean, de-duplicated CSV with all Phase-1 fields populated where available.
- Stays at €0 with OSM-only; stays within Google's free tier when enrichment is enabled.
- Has unit tests for the logic that matters (dedup, presence classification, filtering, mapping).

**Business (judged by the operator on real output)**
- A reviewable share of results are **genuine "no website" or "social-only" leads** worth a visit.
- The `WebPresence` classification is right often enough to trust (spot-check ~30 records).
- OSM coverage gap is *measured* (how many real local businesses are missing) so we know whether
  directory plugins (Phase 1.5) are needed.

The output of the gate is a decision: **continue / improve scoring / change sources / pivot.**

---

## 3. Phase-1 field set (the CSV / DB columns)

Business Name · Address · Postal Code · District · Phone · Website ·
Web Presence (none / social-only / has-site) · Google Rating* · Review Count* ·
Google Maps URL* · Discovered By · Last Updated

\* populated only when Places enrichment is enabled.

### 3a. Validation report format (rendered after every run)

```
Category: Dentist
District: 7

Businesses Collected: 134
Duplicates Removed:    6
Businesses Persisted:  128

No Website:   18
Social Only:  24
Has Website:  86

Enriched:     42       (pipeline health — Google answered)
Not Enriched: 86

Potential Leads: 42    (= No Website + Social Only — NOT enrichment count)

Run Duration: 2m 18s
Generated At: 2026-06-26T14:05:11Z
Run ID:       2026...-d7-dentist
```

Corrected definition: **Potential Leads = No Website + Social Only**, derived from web presence,
independent of enrichment. `Enriched` is reported separately as a pipeline-health signal. Future
metrics (OSM coverage, Google match rate, category/district comparison) are added by extending
`RunReport` and querying persisted run history — no re-architecture.

---

## 4. Build order (module by module, inside-out)

Each milestone lands with its tests before the next starts. Estimates are build-time, not elapsed.

| # | Milestone | What ships | Def. of done | Est. |
|---|---|---|---|---|
| M0 | **Project skeleton** | repo layout, `pyproject.toml`, ruff/mypy/pytest config, logging, `.env.example` | `pytest` runs green on an empty suite; lint passes | 1–2h |
| M1 | **Core domain** | `core/models.py`, `core/enums.py`, `core/interfaces.py` | models validate; interfaces import cleanly; unit tests on model validation | 2–3h |
| M2 | **Config + regions** | `config/settings.py`, `regions/vienna.yaml` (PLZ↔district, category→OSM tags) | loader returns typed config; district↔PLZ mapping unit-tested | 1–2h |
| M3 | **OSM DataSource** | `collector/osm_source.py` (Overpass query → `Business`) | discovers a district+category against a recorded fixture; rate-limited; mapping tested | 2–4h |
| M4 | **Dedup** | `collector/dedup.py` | within-source dedup by source id + name/geo; unit tests on known dup sets | 1–2h |
| M5 | **Website presence** | `website_checker/presence.py` | classifies NONE / SOCIAL_ONLY / HAS_SITE from available signals; tested | 1–2h |
| M6 | **Repository (SQLite)** | `database/orm.py`, `database/repository.py` | upsert/get/find/find_match/soft_delete work; idempotent upsert tested | 2–3h |
| M7 | **CSV Exporter** | `exporters/csv_exporter.py` | writes the Phase-1 field set; tested on sample businesses | 0.5–1h |
| M8 | **Pipeline + CLI** | `pipeline.py`, `cli/main.py` | `sitefinder run …` executes M3→M7 end to end, builds & returns a `RunReport`; budget/freshness honored | 2–3h |
| M9 | **Validation report** | `reports/validation.py`, `RunReport` model, optional `run_reports` table | report renders to console + file after each run; `potential_leads = no_website + social_only`; rendering unit-tested on a sample `RunReport` | 1–2h |
| M10 | **Optional Places enricher** | `enricher/places_enricher.py` | `--enrich places` adds rating/reviews/place_id for survivors only, field-masked, cached; off by default; feeds enriched/not-enriched counts into the report | 2–3h |
| M11 | **Validation run + write-up** | run Dentist/Hair Salon/Restaurant × a few districts; collect the auto-generated reports | filled CSVs + run reports + a short findings note feeding the decision gate | 1–2h |

**Total:** ~16–29h nominal; the ~10–20h target is hit by treating **M10 (Places) as optional** and
keeping M0–M9 lean. M10 and M11 can slip past the first validation pass if OSM-only already answers
the business question. M9 is cheap because the pipeline already assembles the `RunReport` (M8) — the
reporter only renders it.

---

## 5. Sequencing rationale

We build **inside-out** (core → plugins → pipeline) so that:
- the contracts (M1) are fixed before anything implements them — no churn;
- every plugin is independently testable against fixtures before integration;
- the first *runnable* end-to-end result (M8) appears with the cheapest possible source (OSM),
  so we learn about lead quality before spending a cent on Places.

`analyzer/` and `lead_scoring/` stay empty placeholders in Phase 1 — present in the structure,
deliberately unbuilt, per risk **R8** (don't over-engineer the MVP).

---

## 6. Explicitly out of scope for Phase 1

Website quality audit, lead scoring beyond presence, CRM/notes/visit status, AI summaries,
PDF reports, dashboard/map, multi-city configs, directory scraper plugins (Herold/FirmenABC),
Postgres. All are *accommodated* by the architecture and scheduled for later phases.

---

## 7. Post-Phase-1 decision gate

After M10, we review the real leads together and choose a direction:

- **Continue** → build Phase 2 (website audit + real lead scoring).
- **Improve scoring** → the leads exist but ranking is weak; iterate on classification/criteria.
- **Change / add sources** → OSM coverage gap too large; prioritize the directory scraper plugins.
- **Pivot** → the lead quality doesn't support the in-person sales model; rethink the value prop.

This gate is the entire point of treating Phase 1 as validation: the next investment is justified
by evidence, not by the sunk cost of the architecture.
