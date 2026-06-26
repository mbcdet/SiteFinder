# SiteFinder — Architecture

> **Status:** Frozen for Phase 1 (proposed → pending final approval)
> **Owner:** Architecture & technical lead
> **Last updated:** 2026-06-26

SiteFinder is a modular, provider-agnostic lead-generation platform. Its purpose is
**not** data collection for its own sake — it is to identify local businesses (initially
in Vienna, Austria) that have **no website** or a **poor website**, rank them by how
likely they are to buy web-development services, and feed that list to a human who will
approach them in person.

This document is the single source of truth for the system's structure. It describes
*what exists and why*, not *how it is coded*. Implementation follows, module by module,
only after this is approved.

---

## 1. Goals and non-goals

### Goals
- Produce **ranked, de-duplicated, actionable leads** for a chosen category + Vienna district.
- Be **provider-agnostic**: no external data source is load-bearing or mandatory.
- Keep recurring operating cost at or near **€0** for personal-scale use.
- Be **extensible**: new cities, countries, categories, data sources, audit rules, and
  AI features should require *adding* code, not *rewriting* it.
- Treat **Phase 1 as both the technical MVP and the business validation** — small,
  cheap, ~10–20 hours, then judged on real lead quality.

### Non-goals (Phase 1)
- No website quality audit, no lead *scoring beyond presence*, no CRM, no dashboard,
  no AI summaries. These are Phases 2–4 and are only *accommodated* by the architecture,
  not built yet.
- No multi-user, no auth, no hosted service. This is a single-operator local tool.

---

## 2. Guiding principles

1. **Dependency inversion.** The core domain (models + interfaces) depends on nothing.
   Everything else depends on the core. Data sources, the database, exporters, and audit
   rules are *plugins* that implement core interfaces.
2. **Acquisition method is a per-source property.** Each source chooses its natural access
   path — free API, paid API, or browser automation — behind one common interface. We do
   not globally prefer "API" or "scraping."
3. **Ownership lives in the store, not the source.** Once a business is normalized and
   persisted, we own that record. Providers are swappable front-ends to data we already hold.
4. **Free first, paid optional, scrape only where there's no API.** OSM (free API) is the
   primary Phase-1 source. Google Places is an *optional* paid enrichment plugin, off by
   default. Browser-automation plugins (e.g. Austrian directories) are reserved for
   high-value sources that expose no API.
5. **Config over code.** Districts, postal codes, and category mappings are data files.
   A new city is a new config file, not a new module.
6. **Compliance is a design input, not an afterthought.** GDPR retention/erasure, EU
   database rights, and source ToS shape the data model and acquisition limits from day one.
7. **Self-documenting code, thin modules.** No monolithic files; each module has one reason
   to change.

---

## 3. Architectural style

A **layered, plugin-oriented architecture** with strict inward-pointing dependencies:

```
            ┌────────────────────────────────────────────┐
            │                   cli / ui                  │  (drives the pipeline)
            └───────────────────────┬────────────────────┘
                                    │
            ┌───────────────────────▼────────────────────┐
            │                  pipeline                   │  (orchestration only)
            └───────────────────────┬────────────────────┘
                                    │ depends on interfaces, never concretions
            ┌───────────────────────▼────────────────────┐
            │        core: models + interfaces (ABCs)     │  ← depends on NOTHING
            └───────────────────────▲────────────────────┘
                                    │ implemented by
   ┌──────────────┬─────────────────┼──────────────────┬───────────────┐
   │ collector    │ enricher        │ website_checker  │ database       │ exporters
   │ (DataSource) │ (Enricher)      │ (WebsiteChecker) │ (Repository)   │ (Exporter)
   └──────────────┴─────────────────┴──────────────────┴───────────────┘
        plugins — interchangeable implementations of core interfaces
```

The **pipeline** wires plugins together but knows them only by their interface. Swapping
OSM for another source, or SQLite for Postgres, touches one wiring line and one plugin —
never the pipeline logic or the domain.

---

## 4. End-to-end data flow (Phase 1)

```
config (district → PLZ, category → OSM tags)
        │
        ▼
[1] DataSource.discover()            OSM / Overpass (free)
        │   raw places
        ▼
[2] normalize → Business             map raw shape → domain model
        │
        ▼
[3] dedup                            stable key per source; cross-source merge
        │
        ▼
[4] free pre-filter                  district (PLZ), category — no API cost
        │   survivors only
        ▼
[5] Enricher.enrich()  (optional)    Google Places: rating, reviews, website, place_id
        │   skip if cached & fresh
        ▼
[6] WebsiteChecker.classify()        WebPresence: NONE / SOCIAL_ONLY / HAS_SITE
        │
        ▼
[7] Repository.upsert()              SQLite (own the data)
        │
        ▼
[8] Exporter.export()                CSV
        │
        ▼
[9] Reporter.render(RunReport)       validation report (console + file)
```

The pipeline accrues a **`RunReport`** across every stage (counts at each boundary + timing) and
returns it; the `Reporter` renders it at the end. See §8a for instrumentation rules.

Steps 5 is optional and budget-gated. With OSM-only and Places disabled, the pipeline
still produces presence-classified leads at €0; enabling Places adds rating/reviews for the
filtered survivors only, keeping us inside the free tier.

---

## 5. Repository structure

```
sitefinder/
├── pyproject.toml                  # packaging, deps, tool config
├── README.md
├── ARCHITECTURE.md                 # this document
├── ROADMAP_PHASE1.md
├── .env.example                    # API keys, budget knob (never commit real .env)
│
├── sitefinder/                     # the package
│   ├── __init__.py
│   │
│   ├── core/                       # depends on NOTHING in the app
│   │   ├── models.py               # Business, Location, WebPresence, Rating, Contact, Provenance
│   │   ├── enums.py                # WebsiteStatus, SourceName, etc.
│   │   └── interfaces.py           # DataSource, Enricher, Repository, WebsiteChecker, Exporter (ABCs)
│   │
│   ├── config/
│   │   ├── settings.py             # env-backed app settings (pydantic-settings)
│   │   └── regions/
│   │       └── vienna.yaml         # 23 districts → PLZ; category → OSM tag mapping
│   │
│   ├── collector/                  # DataSource implementations
│   │   ├── osm_source.py           # Overpass discovery (Phase 1 primary)
│   │   └── dedup.py                # within- and cross-source de-duplication
│   │
│   ├── enricher/                   # Enricher implementations
│   │   └── places_enricher.py      # Google Places (optional, paid, off by default)
│   │
│   ├── website_checker/            # WebsiteChecker implementations
│   │   └── presence.py            # Phase 1: NONE / SOCIAL_ONLY / HAS_SITE
│   │
│   ├── analyzer/                   # Phase 2 placeholder (audit rules engine)
│   │   └── __init__.py
│   │
│   ├── lead_scoring/               # Phase 2 placeholder (rules-based scoring)
│   │   └── __init__.py
│   │
│   ├── database/                   # Repository implementation
│   │   ├── repository.py           # SqliteRepository (stdlib sqlite3)
│   │   └── schema.sql              # table definitions (businesses, run_reports)
│   │
│   ├── exporters/                  # Exporter implementations
│   │   └── csv_exporter.py
│   │
│   ├── reports/                    # run-level validation reporting
│   │   └── validation.py           # renders a RunReport (console + file)
│   │
│   ├── infra/                      # cross-cutting plumbing
│   │   ├── http.py                 # shared httpx client, retries, timeouts
│   │   ├── cache.py                # request/response + freshness cache
│   │   ├── rate_limit.py           # token-bucket per source
│   │   └── logging.py              # structured logging setup
│   │
│   ├── pipeline.py                 # orchestrates the flow; depends only on interfaces
│   └── cli/
│       └── main.py                 # Typer entrypoint
│
└── tests/
    ├── unit/                       # models, dedup, presence, filters (fast, no network)
    ├── integration/               # source/enricher against recorded fixtures (VCR-style)
    └── fixtures/                   # canned Overpass / Places responses
```

**Why this shape:** `core/` is the contract everyone shares and has zero dependencies, so
it can never be broken by a plugin. Each plugin family (`collector`, `enricher`, …) is a
folder so new implementations sit side by side without touching siblings. `infra/` holds the
boring-but-critical concerns (HTTP, cache, rate limiting) so plugins don't each reinvent them.
`pipeline.py` is deliberately thin — orchestration is not business logic.

---

## 6. Domain models

The domain model is the **contract every module speaks**. Plugins translate their raw,
source-specific shapes into these types at the boundary; nothing downstream ever sees a raw
Overpass element or a Places JSON blob. Models are **Pydantic v2** (validation + serialization
for free) and are intentionally provider-neutral.

```python
# core/enums.py  (design contract — not final implementation)

class SourceName(str, Enum):
    OSM = "osm"
    GOOGLE_PLACES = "google_places"
    HEROLD = "herold"            # future
    FIRMENABC = "firmenabc"      # future

class WebsiteStatus(str, Enum):
    NONE = "none"                # no website and no social presence found
    SOCIAL_ONLY = "social_only"  # only Facebook/Instagram/etc. — a strong lead
    HAS_SITE = "has_site"        # an actual website exists
    UNKNOWN = "unknown"          # not yet checked
```

```python
# core/models.py  (design contract)

class Location(BaseModel):
    latitude: float
    longitude: float
    street: str | None
    postal_code: str | None      # PLZ — the district key in Vienna (1010 → District 1)
    city: str | None
    country_code: str = "AT"     # ISO 3166-1 alpha-2; enables multi-country later
    district: int | None         # derived from postal_code via region config

class Contact(BaseModel):
    phone: str | None
    email: str | None            # collected sparingly; see GDPR notes (§12)

class Rating(BaseModel):
    score: float | None          # e.g. Google 0.0–5.0
    review_count: int | None
    source: SourceName

class WebPresence(BaseModel):
    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    website_url: str | None
    social_urls: list[str] = []
    checked_at: datetime | None

class Provenance(BaseModel):
    """Where each record/field came from — required for ownership, dedup, and compliance."""
    discovered_by: SourceName
    enriched_by: list[SourceName] = []
    source_ids: dict[str, str] = {}   # e.g. {"osm": "node/123", "google_places": "ChIJ..."}
    first_seen: datetime
    last_updated: datetime
    last_enriched: datetime | None

class Business(BaseModel):
    """The central aggregate. The only type the pipeline and repository pass around."""
    id: str                      # internal stable UUID (independent of any provider)
    name: str
    category: str                # normalized internal category
    location: Location
    contact: Contact
    rating: Rating | None
    web_presence: WebPresence
    provenance: Provenance
    is_deleted: bool = False     # soft-delete for GDPR erasure without losing audit trail


class RunReport(BaseModel):
    """Structured summary of one pipeline execution. Built by the pipeline, rendered by
    the Reporter, optionally persisted for historical comparison. Pure data, no I/O."""
    run_id: str
    category: str
    district: int
    source: SourceName
    enricher: SourceName | None

    collected: int               # raw businesses discovered (pre-dedup)
    duplicates_removed: int
    persisted: int

    no_website: int
    social_only: int
    has_website: int

    enriched: int                # pipeline-health metric (Google answered)
    not_enriched: int

    # business-quality metric — DERIVED from presence, NOT from enrichment:
    # potential_leads = no_website + social_only
    potential_leads: int

    started_at: datetime
    finished_at: datetime
    duration_seconds: float
```

**Design decisions worth noting:**
- **Internal `id` (UUID), not `place_id`.** A business may be seen by multiple sources; tying
  identity to one provider's ID would break the provider-agnostic promise. Provider IDs live in
  `Provenance.source_ids` and are used for matching/dedup, not as the primary key.
- **`WebPresence` is a value object, not a boolean.** `SOCIAL_ONLY` is a distinct, often
  *higher-value* lead segment. A boolean would discard your best prospects.
- **`Provenance` is first-class.** It powers dedup, freshness/caching decisions, and the
  audit trail GDPR effectively requires.
- **`postal_code` is the district key.** Vienna PLZ (1010–1230) maps cleanly to districts 1–23,
  avoiding polygon geometry and generalizing to other cities.
- **`potential_leads` is derived from presence, not enrichment.** It is `no_website + social_only` —
  the businesses actually worth visiting. `enriched`/`not_enriched` is a separate *pipeline-health*
  signal and must never be confused with lead count.
- **`country_code` from day one.** Multi-country was a stated goal; baking it in now costs
  nothing and avoids a painful migration later.

---

## 7. Interfaces (the six contracts)

These ABCs are the seams that make the system extensible. Each is small, single-purpose,
and depends only on domain models.

```python
# core/interfaces.py  (design contracts — signatures, not implementations)

class DataSource(ABC):
    """Discovers raw businesses for a query and returns them as normalized Business objects.
    One implementation per source (OSM, future Herold/FirmenABC scrapers, etc.)."""
    name: SourceName

    @abstractmethod
    def discover(self, query: DiscoveryQuery) -> Iterable[Business]: ...
    # query carries: category, region (city/district/PLZ), limits.
    # Implementations own their access method (API or browser automation) internally.


class Enricher(ABC):
    """Adds/updates fields on an existing Business (rating, reviews, website, provider IDs).
    Optional and composable; the pipeline may run zero or many enrichers."""
    name: SourceName

    @abstractmethod
    def enrich(self, business: Business) -> Business: ...
    @abstractmethod
    def supports(self, business: Business) -> bool: ...   # e.g. only if geolocated


class WebsiteChecker(ABC):
    """Determines web presence / (Phase 2) audits a site's quality."""
    @abstractmethod
    def classify(self, business: Business) -> WebPresence: ...


class Repository(ABC):
    """Persistence boundary. Hides the storage engine from the rest of the app
    so SQLite → Postgres is a one-plugin change."""
    @abstractmethod
    def upsert(self, business: Business) -> None: ...
    @abstractmethod
    def get(self, business_id: str) -> Business | None: ...
    @abstractmethod
    def find(self, criteria: QueryCriteria) -> list[Business]: ...
    @abstractmethod
    def find_match(self, business: Business) -> Business | None: ...  # for cross-source dedup
    @abstractmethod
    def soft_delete(self, business_id: str) -> None: ...              # GDPR erasure


class Exporter(ABC):
    """Renders a set of businesses to an output format (CSV now; XLSX/JSON/PDF later)."""
    @abstractmethod
    def export(self, businesses: Iterable[Business], destination: Path) -> Path: ...


class Reporter(ABC):
    """Renders a RunReport to a destination (console + text file now; JSON/markdown later).
    Pure presentation — the pipeline builds the RunReport; the Reporter never computes metrics."""
    @abstractmethod
    def render(self, report: RunReport, destination: Path | None = None) -> str: ...
```

**Why these six, and not fewer or more:** discovery and enrichment are genuinely different
operations (one *finds*, one *augments*) with different cost profiles and cadence, so they are
separate interfaces — this is what lets Google be enrichment-only. `WebsiteChecker` is split
out because presence-now and quality-audit-later are the same conceptual responsibility and
should evolve in one place. `Repository` and `Exporter` are classic boundaries that protect us
from storage- and format-lock-in. `Reporter` is separate from `Exporter` because they render
*different subjects*: `Exporter` renders **business data** (the deliverable), `Reporter` renders
**run metadata** (the validation summary). Same pattern, different concern — keeping them apart
avoids a leaky interface that knows about both.

---

## 8. Module catalog — purpose and communication

| Module | Reason to exist | Talks to | Via |
|---|---|---|---|
| `core` | The shared contract; zero deps so it can't break | (nobody; everyone depends on it) | imports |
| `config` | Turn cities/categories into data, not code | pipeline, collector | typed settings + YAML |
| `collector` | Discover businesses per source | core models, infra | implements `DataSource` |
| `enricher` | Optionally augment with paid/extra data | core models, infra, cache | implements `Enricher` |
| `website_checker` | Classify presence (P1), audit quality (P2) | core models, infra | implements `WebsiteChecker` |
| `database` | Persist and query; own the data | core models | implements `Repository` |
| `exporters` | Emit deliverables (CSV now) | core models | implements `Exporter` |
| `reports` | Render run-level validation summary | core models (`RunReport`) | implements `Reporter` |
| `infra` | HTTP, caching, rate limiting, logging | (used by plugins) | plain functions/clients |
| `pipeline` | Orchestrate the flow, enforce budget & freshness, build `RunReport` | all interfaces | depends on ABCs only |
| `cli` | Operator entrypoint | pipeline, config | Typer commands |

**Communication rule:** modules never import each other's concretions. The pipeline receives
concrete plugins (constructed at the composition root in `cli/main.py`) but operates on them
through interfaces. This is the single discipline that keeps the system swappable.

### 8a. Run instrumentation & reporting

The validation report is built from data only the orchestrator can see (pre-dedup counts,
timing, enrichment outcomes), so:

- **The pipeline collects metrics, not the plugins.** As it moves through stages, the pipeline
  records counts at each boundary (collected → after-dedup → persisted; presence breakdown;
  enriched vs not) and timestamps, assembling a `RunReport`. Individual plugins stay unaware that
  reporting exists — they just transform `Business` objects.
- **The pipeline returns the `RunReport`; it does not print it.** Rendering and file I/O are the
  `Reporter`'s job, invoked by the CLI. This keeps the pipeline pure and unit-testable (assert on
  the returned `RunReport`, no stdout capture).
- **`potential_leads` is derived, never an alias for `enriched`.** It equals `no_website +
  social_only`. Enrichment counts measure whether Google answered, not lead quality.
- **`RunReport` is optionally persisted** (a `run_reports` table via the repository). This is what
  turns the "later" metrics — category comparison, district comparison, match-rate trends — into
  simple queries over run history rather than new architecture.

---

## 9. Data acquisition strategy

Tiered, decided per source:

1. **Free official API — primary.** OSM via Overpass. No key, broad tag coverage, legal to use
   within fair-use limits. Phase 1 ships with this as the only discovery source.
2. **Paid API — optional enrichment.** Google Places (New), behind a budget flag, **off by
   default**. Enriches only filtered survivors; uses field masks to stay in the cheapest SKU
   tier and respects per-SKU monthly free caps. Provides rating, review count, authoritative
   website, and `place_id`.
3. **Browser automation — scoped, future.** Austrian directories (Herold, FirmenABC) expose no
   public API; a Playwright-backed `DataSource` plugin is the legitimate path *for those
   sources only*. Introduced in Phase 1.5 once the interface is proven. **Google is never
   scraped** — its API exists and scraping it violates ToS regardless of technique.

**Matching across sources (the hybrid cost):** OSM has no Google ID, so enriching an OSM
business with Places requires a Places text/match call per candidate. This is exactly why
enrichment runs *after* the free filter — we pay (in API quota) only for businesses we've
already decided are worth contacting.

---

## 10. Persistence and ownership

- **Engine:** SQLite via **stdlib `sqlite3`** for Phase 1, accessed **only** through the
  `Repository` interface. No ORM — the project scope ends at Phase 1, so a zero-dependency
  persistence layer is the right call. The `Repository` abstraction is unchanged, so SQLAlchemy
  or Postgres can be introduced later as a new implementation without touching any other module
  (blast radius: one folder).
- **Identity & dedup:** internal UUID primary key; provider IDs stored in `provenance.source_ids`
  with unique indexes for fast match lookups. `Repository.find_match` enables cross-source merge.
- **Freshness:** `provenance.last_enriched` drives a TTL — the pipeline skips re-enriching fresh
  records, which is what keeps repeat runs inside the free tier.
- **Ownership:** because every record is persisted with provenance, the collected dataset
  outlives any single provider. The store *is* the asset.

---

## 11. Configuration and extensibility

Extensibility is concrete, not aspirational. Each future need maps to a specific, low-blast-radius change:

| To add… | You… | You do NOT… |
|---|---|---|
| A new Vienna category | add a tag mapping to `vienna.yaml` | touch any module |
| A new city | add `regions/<city>.yaml` | change the pipeline |
| A new country | add a region file (+ later, country-specific rules) | restructure models (`country_code` exists) |
| A new data source | add a `DataSource` plugin, register it at the composition root | modify other sources |
| A new enricher | add an `Enricher` plugin | change discovery |
| A new export format | add an `Exporter` plugin | change anything upstream |
| A Phase-2 audit rule | add a rule to the analyzer's rule set | rewrite the checker |

---

## 12. Cross-cutting concerns

- **HTTP:** one shared `httpx` client with sane timeouts, connection pooling, and retry/backoff
  for transient failures.
- **Caching:** responses and enrichment results are cached with TTL; re-runs are cheap and quota-friendly.
- **Rate limiting:** a per-source token bucket enforces Overpass/Nominatim fair-use (~1 req/s) and
  Places quotas. Lives in `infra`, applied by plugins.
- **Configuration:** `pydantic-settings` loads from environment / `.env`; secrets never hard-coded.
- **Logging:** structured logging from day one (run id, source, counts) — essential for judging a
  validation run.
- **Error handling:** a failed source or enricher degrades gracefully (logged, skipped) rather than
  aborting a whole run; partial results are still persisted.

### Legal / compliance constraints (design inputs)
- **GDPR:** business records of sole traders can be personal data. We minimize collected fields
  (avoid employee personal data; collect email sparingly), store `provenance`, support **soft-delete
  erasure**, and apply a retention TTL. In-person outreach (the actual go-to-market) is the
  lowest-risk channel; this tool must not silently become a cold-email engine without revisiting
  Austrian §174 TKG 2021.
- **EU database right (sui generis):** extracting a *substantial part* of a compiled directory
  (Herold/FirmenABC) can infringe their database right independent of ToS. Scraper plugins must take
  modest, targeted slices — another reason directory scraping is a scoped, later addition.
- **Source ToS:** respected per source; Google is API-only.

---

## 13. Remaining architectural risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | OSM coverage of tiny businesses is patchy/stale | Real leads missed in discovery | Accept for Phase 1; measure miss-rate during validation; directory plugins (P1.5) backfill |
| R2 | OSM↔Google matching is imperfect (name/geo fuzzy) | Wrong rating attached, or no match | Conservative match thresholds; store match confidence; leave unmatched as presence-only leads |
| R3 | Places free-tier caps / pricing change | Enrichment cost creeps up | Off by default; field masks; freshness TTL; hard budget cap in config |
| R4 | "Poor website" is subjective (Phase 2) | Lead score becomes noise | Defer to P2; design audit as explainable, objective rule set |
| R5 | Overpass fair-use / throttling | Slow or failed discovery | Rate limiter + cache; option to self-host Overpass if it scales |
| R6 | GDPR / database-right missteps | Legal exposure | Data minimization, soft-delete, retention TTL, scoped scraping (§12); confirm specifics with counsel |
| R7 | Category taxonomy drift across sources | Inconsistent filtering | Normalize to an internal category in each plugin's boundary mapping |
| R8 | Over-engineering the MVP | Blows the 10–20h budget | Phase-1 ships the thin slice only; placeholders (analyzer, lead_scoring) stay empty |
| R9 | Misleading validation metrics (e.g. leads≡enriched) | Wrong continue/pivot decision | `potential_leads` derived from presence; metric definitions fixed in `RunReport` (§6, §8a) |

R8 is the one I'd watch most as technical lead: the architecture is designed for years, but
Phase 1 must stay a weekend-scale build. The interfaces are cheap to define; resist filling the
Phase-2/3 folders early.

---

## 14. Technology stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Stated preference; ecosystem fit |
| Packaging | `pyproject.toml` (PEP 621), `uv` or `pip` | Standard, reproducible |
| Models / validation | **Pydantic v2** | Validation + (de)serialization; clean domain contracts |
| Settings | **pydantic-settings** | Typed env/.env config |
| HTTP | **httpx** | Modern, timeouts, sync now / async-ready later |
| OSM discovery | **Overpass API** (via httpx) | Free, no key, rich tags |
| Geocoding helper | **Nominatim** (sparingly) | PLZ/district fallback; fair-use limited |
| Enrichment (optional) | **Google Places API (New)** | Authoritative rating/reviews/website |
| Persistence | **SQLite (stdlib `sqlite3`)** | Zero-dependency; Repository abstraction keeps Postgres/SQLAlchemy a later drop-in |
| CLI | **Typer** | Minimal, typed, great DX |
| Export | **csv** stdlib (P1); xlsx via skill later | No dep for the MVP deliverable |
| Browser automation (P1.5) | **Playwright** | For no-API directory sources only |
| Testing | **pytest** + recorded HTTP fixtures | Fast unit tests; deterministic integration |
| Lint/format | **ruff** + **mypy** | Consistency and type safety |
| Logging | stdlib `logging`, structured | Observability for validation runs |

Dependencies are intentionally few. The one judgment call against "minimal deps" is SQLAlchemy,
justified in §10.

---

## 15. What "approved" unlocks

On approval, implementation proceeds **module by module** per `ROADMAP_PHASE1.md`, starting from
`core` (models + interfaces) outward, each module landing with tests before the next begins.
No Phase-2+ code is written until Phase-1 validation results are in.
