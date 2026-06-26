# Phase 1 — Critical Self-Review & Phase 2 Recommendation

> Author: acting CTO / lead engineer. Written at Phase 1 completion, before any Phase 2 work.

## What was built

A complete, modular Phase 1 MVP matching the frozen architecture: config-driven region
loading, OSM (Overpass) discovery, normalization to a `Business` domain model,
de-duplication, web-presence classification (`none` / `social_only` / `has_site`),
idempotent SQLite persistence behind a `Repository`, CSV export, a per-run validation
`RunReport`, an optional (off-by-default) Google Places enricher, and a Typer CLI. ~31 unit
tests plus an end-to-end run.

## How it was verified

My build sandbox has no network and cannot install the third-party stack, so live Overpass
and Places calls could not run here. To compensate, the **real module code** was executed
end-to-end against representative OSM-shaped fixtures via a throwaway compatibility shim
(never part of the repo). That run produced a correct CSV and validation report and passed
every critical invariant: collected/dedup/persisted accounting, the presence breakdown,
`potential_leads = no_website + social_only`, Facebook-as-website demotion to `social_only`,
idempotent re-runs (no duplication), enrichment counting, and the Places field-mask/mapping.

**The engine is validated. The business question is not yet** — that requires one real local
run (`pytest`, then `sitefinder run` against live Vienna data), which is the first thing to do.

## Strengths

- **Clean separation via interfaces.** Swapping the data source, storage, or export format is
  a one-plugin change; the pipeline depends only on abstractions. The sqlite3-for-SQLAlchemy
  swap we made mid-project touched exactly one folder, which proves the boundary works.
- **Idempotent by construction.** `place_id`/OSM-id-based matching means re-running a district
  updates rather than duplicates — safe to run weekly.
- **Honest, decision-useful metrics.** `potential_leads` is presence-derived, kept distinct
  from the `enriched` pipeline-health number — so the headline figure won't mislead the go/no-go.
- **Cost discipline.** OSM-only is free; Places is opt-in, survivor-only, field-masked, and
  freshness-cached.

## Weaknesses & technical debt (honest list)

1. **OSM coverage hinges on `addr:postcode`.** Discovery filters by postcode within the city
   area, so businesses whose OSM entry lacks a postcode tag are silently missed. This is the
   single biggest threat to lead quality and is currently **unmeasured** — the real run must
   sanity-check counts against your local knowledge of a district.
2. **Presence is tag-based, not fetched.** `has_site` means "a non-social URL exists in OSM,"
   not "a live, working site." A dead/parked domain reads as `has_site`; a real site missing
   from OSM reads as `none`. Verifying liveness/quality is deliberately Phase 2.
3. **`find_match` name+postcode fallback can over-merge.** Two genuinely different businesses
   sharing a name and postcode would collapse. Rare, and `osm_id` is the primary key, but it's
   a known sharp edge.
4. **No admin-boundary fallback.** We rely on postcode rather than the Bezirk polygon; simpler,
   but it inherits weakness #1.
5. **Single-process rate limiter, synchronous I/O.** Fine for per-district runs; not built for
   bulk parallel city sweeps (intentionally — that's not the MVP).

None of these are blockers for using the tool; #1 and #2 are the ones that could distort the
validation verdict, so measure them explicitly.

## Phase 2 recommendation

**Do not start Phase 2 yet.** Run the tool for real first, then decide against these criteria:

- **Go (build Phase 2 website-audit + scoring)** if a real run across Dentist / Hair Salon /
  Restaurant over a few districts yields a meaningful `potential_leads` count *and* a ~30-record
  spot-check shows the presence classification is trustworthy *and* the OSM coverage gap looks
  acceptable.
- **Fix sources first (Phase 1.5: Herold/FirmenABC plugins)** if coverage is the bottleneck —
  i.e. you know many real local businesses that never appeared. No amount of Phase-2 auditing
  helps if discovery is missing the leads.
- **Reconsider the value prop** if even with good coverage the `none`/`social_only` segment is
  too small to sustain weekly in-person outreach.

My engineering read: the architecture is sound and extensible, and the most valuable next
investment is almost certainly **better discovery coverage**, not audit sophistication —
because lead *quantity and reach* gate this business before lead *scoring* does. But that's a
hypothesis to confirm with the real run, not an assumption to build on.
