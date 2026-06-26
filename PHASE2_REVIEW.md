# Phase 2 — Engineering Review

> Acting CTO. Website audit, quality analysis, and lead scoring, plus an interactive optional
> Google Places enrichment stage. Challenged honestly, not defended.

## What was built

- **Lead model with provider provenance** — `website_osm` / `website_google` kept raw, derived
  `effective_website` (social-aware) and `website_match` (MATCH/OSM_ONLY/GOOGLE_ONLY/DIFFERENT/NONE).
- **Audit engine** — fetch-once `SiteSnapshot` + eight pure checkers (SSL, mobile, performance,
  SEO, contact, site-health, accessibility, booking); `WebsiteAuditor` aggregates a weighted score.
- **Lead scoring** — transparent rules: no/poor website ranks highest; optional reputation bonus
  from Google reviews (only when enrichment ran).
- **Interactive enrichment** — post-discovery prompt (Continue free / Google Places), count
  selection, and a pre-flight preview (total, selected, cached, new requests, estimated cost &
  time) requiring explicit confirmation before any API call.
- **Outputs** — `leads.csv`, `leads_enriched.csv`, `report.txt`, `audit_report.txt`,
  `final_report.txt`; nothing is overwritten.

## How it was verified

Sandbox has no network and can't install the stack, so the real modules were exercised end-to-end
via a compatibility shim with injected fetchers/clients. Validated: free and enriched workflows
produce identical audit-based ranking (no-website 90 > social 80 > poor site 65 > good site 0),
the reputation bonus appears only when enriched, each checker scores correctly, no-website leads
are scored with zero fetches, and the Phase 1 flows still pass. The full `pytest` suite (now incl.
audit checkers, aggregation, scoring, pipeline, dual-website provenance) runs locally.

## Strengths

- **Workflow A/B parity is structural, not conventional.** Audit/scoring read only the normalized
  `Business`; they genuinely cannot tell whether Google ran. Google remains strictly optional.
- **Fetch-once + pure checkers** is the high-value design call: one network call per site, every
  check deterministic and offline-testable, and new checks are a one-file addition.
- **Explainable scoring.** Every lead score carries human reasons (the audit weak areas, presence,
  reputation) — directly useful for deciding who to visit and what to pitch.
- **Cost safety.** No API request is sent without a preview and confirmation; caching makes
  re-runs free.

## Weaknesses & technical debt (honest)

1. **HTML heuristics are regex-based, not a DOM parse.** Robust enough for "is there a viewport /
   title / alt text", but it will misjudge JS-rendered SPAs (empty initial HTML → looks poor) and
   can be fooled by unusual markup. A real headless render (Playwright) would be more accurate —
   deliberately deferred (heavy dependency, slow).
2. **Performance check is a single-request latency proxy**, not Core Web Vitals. It flags slow
   servers, not render performance. Documented as coarse.
3. **"Broken links" is a site-health proxy**, not a crawl — it checks the primary page, not every
   link (crawling multiplies requests). Named `site_health` to avoid overclaiming.
4. **Audit results aren't persisted/cached.** Each run re-fetches sites. Fine at per-segment scale;
   a snapshot cache (mirroring the Places freshness cache) is the obvious next improvement.
5. **No concurrency.** Audits are sequential; a 200-lead district audit is I/O-bound and slow.
   The pure-checker design makes adding async/threaded fetching safe later.
6. **Booking/contact keyword lists are German/Austrian-biased** — correct for Vienna, needs
   extension per locale (already isolated in one place each).

## Maintainability

High. Each checker is ~15 lines, single-responsibility, independently testable; the auditor is a
thin orchestrator. Scoring is one small, tunable function. The five interfaces and the normalized
model keep stages decoupled — Phase 2 added modules without modifying Phase 1 logic beyond the
additive `WebPresence` provenance fields.

## Scalability

- **More checks**: trivial (one file + one registration line).
- **More leads/districts**: bounded by sequential audit fetches (weakness #5); async + a snapshot
  cache are the unlocks, both compatible with the current design.
- **More cities/countries**: discovery already config-driven; audit is locale-agnostic except the
  keyword lists; scoring is universal.

## Operating & API costs

- **Discovery + audit: €0.** OSM is free; auditing fetches sites directly (bandwidth only).
- **Google Places (optional):** ~$0.017 per enriched lead (higher-tier Text Search with
  rating/reviews/website field mask). Realistic weekly use (`--top 20` over a handful of segments,
  a few hundred calls/month) stays within Google's monthly free allotment → effectively €0.
  The pre-run preview shows the exact estimate before anything is sent.

## Caching effectiveness

The Places freshness cache (repository `last_enriched` + configurable `freshness_days`) means a
business is never queried twice inside the window — validated: a re-run made **zero** API calls.
This is the main cost control. Website-audit caching is **not** yet implemented (weakness #4) and
is the highest-value caching to add next.

## Should Google enrichment stay optional?

**Yes — keep it strictly optional.** The free workflow already answers the core question (who has
no/poor website) and now ranks prospects via the audit. Google adds *prioritization polish*
(ratings to spot established, monied businesses; a second website source for the MATCH/DIFFERENT
signal) — valuable but not load-bearing. Making it default would reintroduce an API-key/cost
dependency for zero gain on the primary goal. The architecture enforces this, and it should stay
that way.

## Recommended next steps (Phase 3 candidates, not started)

1. **Snapshot cache** for audits (biggest cost/time win on re-runs).
2. **Concurrency** for audit fetches.
3. Optional **headless render** for SPA-heavy sites, behind a flag (like Places).
4. Real validation on live Vienna data to tune scoring weights against actual outcomes.

## Git runbook (sandbox can't run git — create-but-not-delete mount)

```bash
rm -f .git/index.lock _deltest.tmp          # clear earlier leftovers if present
git add sitefinder/core/enums.py sitefinder/core/models.py \
        sitefinder/collector/osm_source.py sitefinder/website_checker/presence.py \
        sitefinder/enricher/places_enricher.py sitefinder/pipeline.py \
        sitefinder/exporters/csv_exporter.py tests/
git commit -m "feat(phase2): dual-website provenance in the lead model"

git add sitefinder/analyzer/ sitefinder/infra/http.py
git commit -m "feat(audit): fetch-once SiteSnapshot + modular website checkers"

git add sitefinder/lead_scoring/ sitefinder/audit_pipeline.py \
        sitefinder/reports/audit_report.py sitefinder/reports/final_report.py
git commit -m "feat(scoring): rules-based lead scoring + audit/final reports"

git add sitefinder/config/settings.py sitefinder/enricher/runner.py sitefinder/cli/main.py \
        scripts/run_matrix.sh README.md ARCHITECTURE.md PHASE2_REVIEW.md
git commit -m "feat(cli): interactive optional enrichment + integrated audit stage"

pytest && git push origin main
```
