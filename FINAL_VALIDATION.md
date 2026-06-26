# SiteFinder — Validation & Refinement Report

> Acting CTO / lead engineer. Covers the Phase 1 hardening pass: discovery quality, category
> validation approach, lead-quality analysis, output organization, and the Phase 2 verdict.

## Summary of changes made in this pass

1. **Discovery rewritten to use administrative-boundary search** (the most important change).
2. **Organized output tree** `results/<category>/district_NN/{leads.csv,report.txt}`.
3. **Batch runner** `scripts/run_matrix.sh` for category × district sweeps.
4. **Repo hygiene**: `.gitignore` + untracking of build artifacts.
5. New unit tests for the boundary strategy and district fallback; all prior tests retained.
6. Architecture unchanged — every change lives inside existing modules/config.

## 1. Discovery quality — evaluation & fix

**Finding: the original query was unnecessarily restrictive.** It filtered each element by an
exact `addr:postcode` tag within the city area. In OSM, many small businesses simply don't carry
`addr:postcode`, so they were silently dropped — precisely the businesses (small, low-digital-
maturity) most likely to be good leads. This was the single largest threat to the product's value.

**Fix (architecture-preserving):** discovery now searches **within the district's administrative
boundary** (`area["name"="<Bezirk>"]["admin_level"="9"]`) and no longer requires a postcode tag.
The district is derived from the boundary we searched when the tag is absent. Bezirk names for all
23 districts are in `vienna.yaml`. The old postcode strategy remains as an automatic fallback when
no boundary name is configured (keeps other cities working before they're fully mapped).

Why this is the right lever: Vienna's Bezirk boundaries are core, well-maintained OSM data
(reliable), whereas postcode *tags* on individual POIs are inconsistent. Boundary search trades a
fragile per-element tag dependency for a stable geographic one. Expected effect: materially higher
recall, especially for `no_website` / `social_only` businesses.

Other tag tweaks: added `shop=coffee` to `cafe`; added a `barber` category (note: OSM tags barbers
as `shop=hairdresser`, so it overlaps `hair_salon` by design — the data can't cleanly separate them).

**Validated in-sandbox** against representative fixtures: boundary query is emitted correctly
(admin_level=9, no `addr:postcode`), and a business lacking a postcode tag is now retained with the
correct district. The live query runs against the public Overpass API on your machine.

## 2. Category validation — how to get real numbers

Live Overpass/Places calls require network access my build environment does not have, so I could
not produce real Vienna counts here. The tool and a one-command runner are ready; run locally:

```bash
pip install -e ".[dev]" && pytest          # confirm the suite is green
scripts/run_matrix.sh "dentist hair_salon restaurant cafe barber physiotherapist" "1 6 7 8 15"
```

Then compare the per-run reports:

```bash
grep -H "Potential Leads" results/*/district_*/report.txt | sort -t: -k3 -n
```

**Engineering expectation (hypothesis, to confirm with the run):** restaurants and cafés are
densely mapped in OSM but more likely to already have a website; **hair salons, barbers, and
physiotherapists** are likely to yield the richest `no_website` / `social_only` segments — i.e. the
best web-dev prospects. Dentists tend to skew toward already having sites. Treat this as a
prediction to test, not a result.

## 3. Lead-quality analysis — what to inspect

The report segments every run into `no_website`, `social_only`, `has_website`; **potential leads =
no_website + social_only**. When reviewing real output, check:

- **Genuine no-website / social-only** — the core target. Spot-check ~30 rows: is the classification
  right? (Open a few, confirm they truly lack a site.)
- **Outdated websites** — *not detectable in Phase 1.* Presence is tag-based, not fetched. A live but
  dated/parked site reads as `has_website`. Detecting "poor" sites is exactly Phase 2's job.
- **Suspicious/low-quality results** — chains/franchises (less likely to buy), or a `website` that is
  actually a Facebook link (already auto-demoted to `social_only`).
- **Duplicates** — collapsed by OSM id and by (name, postcode); re-runs are idempotent.
- **Missing businesses** — the key coverage check: pick a block you know and see who's absent. This
  measures the residual OSM gap after the boundary fix and tells you whether directory plugins
  (Herold/FirmenABC) are needed.

## 4. Output organization — done

Runs now write to `results/<category>/district_<NN>/{leads.csv,report.txt}` (override with
`--export`). `results/` and `*.db` are git-ignored so the repo stays clean while history of runs
lives on disk for comparison.

## 5. Git workflow — blocker + runbook

**Blocker:** my sandbox mounts the project **create-but-not-delete**. I can write files but cannot
remove any, including the stale `.git/index.lock` left by a commit attempt (which also failed for a
missing git identity). I therefore could not commit/push from here, and deliberately avoided
alternate-index hacks that risk leaving your repo half-synced. Network is also blocked, so push must
happen from your machine regardless.

**Run locally to commit the improvements cleanly:**

```bash
cd <repo>
rm -f .git/index.lock _deltest.tmp        # remove my leftovers
git reset                                  # clear any half-staged state

# Commit 1 — repo hygiene
git rm -r --cached --quiet sitefinder.egg-info sitefinder.db
git ls-files | grep -E '__pycache__|\.DS_Store' | xargs git rm --cached --quiet
git add .gitignore
git commit -m "chore: add .gitignore and stop tracking build artifacts"

# Commit 2 — discovery improvement
git add sitefinder/config/region.py sitefinder/config/regions/vienna.yaml \
        sitefinder/core/models.py sitefinder/collector/osm_source.py \
        tests/unit/test_osm_source.py ARCHITECTURE.md
git commit -m "feat(discovery): search district admin boundary instead of postcode tag

Captures businesses lacking an addr:postcode tag (major OSM coverage gain).
Adds Bezirk names to config, district_area to the query, a boundary branch in
the Overpass builder, and a district fallback in element mapping. Adds barber
category and shop=coffee for cafe."

# Commit 3 — output organization + tooling
git add sitefinder/cli/main.py scripts/run_matrix.sh README.md
git commit -m "feat(cli): organized results/ output tree and matrix runner"

# Commit 4 — validation docs
git add FINAL_VALIDATION.md PHASE1_REVIEW.md
git commit -m "docs: validation and refinement report"

pytest && git push origin main             # push only if tests pass
```

(Adjust the branch name if not `main`.)

## 6. Engineering review

**Strengths.** Clean interface boundaries (the sqlite3-for-SQLAlchemy and postcode-for-boundary
swaps each touched one area, proving extensibility); idempotent, re-runnable; honest metrics
(`potential_leads` ≠ `enriched`); €0 default cost; now far less dependent on inconsistent OSM tags.

**Weaknesses / debt.** Presence is tag-based, not verified by fetching (no liveness/quality signal —
Phase 2). `find_match` name+postcode fallback can over-merge rare same-name cases. Boundary search
assumes Bezirk relations exist (true for Vienna; must be configured per new city). `barber` overlaps
`hair_salon` due to OSM tagging. Synchronous, single-process (fine for per-district use).

**Remaining risks.** (1) Residual coverage gap after the boundary fix is still *unmeasured* — needs
the real run. (2) Some businesses have a website Google knows but OSM doesn't; only Places enrichment
surfaces that, at API cost. (3) OSM freshness lag.

**Coverage observations.** The boundary fix should be the difference between "only postcode-tagged
businesses" and "all businesses geographically in the district." That is the highest-leverage
change available without adding a new data source.

## Verdict: Phase 2 or Phase 1.5?

**Do not start Phase 2 (website audit + scoring) yet — but you likely don't need a big Phase 1.5
build either.** The most important Phase 1.5 work (discovery coverage) is now done. The honest
sequence is:

1. **Run the real matrix** (section 2) and do the lead-quality spot-check (section 3). This is the
   actual validation; everything above is engineering, not evidence.
2. **If the boundary fix yields enough real no-website / social-only leads** to sustain weekly
   in-person outreach → **start using the tool now**, and let real usage decide whether Phase 2's
   audit/scoring is worth it. My honest read: Phase 2 is premature until you have weeks of real
   leads showing that *ranking*, not *quantity*, is the bottleneck.
3. **Only if the spot-check shows a large residual coverage gap** (businesses you know are missing
   from OSM even after boundary search) → build the **Herold/FirmenABC directory plugins** before
   anything else. No audit feature helps if discovery misses the leads.

Bottom line: the gating question is empirical and one local run away. The architecture is sound, the
biggest discovery weakness is fixed, and I'd bet on "use it and gather real leads" over "build more
features" as the next step.
