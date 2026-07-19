# 03 — MODULE, CLASS, AND FUNCTION CONTRACTS

Behavioral contracts for every module. The stubs' docstrings summarize the SPEC;
this file adds the engineering contract (failure modes, logging, performance,
testing, extension points) and pins internal APIs so parallel agents converge.

**Global rules inherited by every module** (stated once, not repeated below):
- *Config:* only via objects from `epra.common.config`; never re-read YAML (EN-040).
- *Errors:* gate/contract violations raise (fail-fast, EN-061); exceptions carry
  actionable context (what, where, expected vs actual); never swallow exceptions.
- *Logging:* module-level `logging.getLogger(__name__)`; INFO = pipeline
  progress, WARN = non-contract anomaly, ERROR only alongside a raise.
- *Security:* the token exists only in `_fetch`'s request assembly; no module
  ever logs a URL without the token stripped (A-7).
- *Reproducibility:* same inputs ⇒ same outputs, bit-for-bit where a golden/
  checksum exists; all randomness seeded from config; iteration order explicit
  (sorted keys, never set/dict order).
- *Thread safety:* the pipeline is single-process, single-threaded by design
  (ING-007 forbids parallel requests; DuckDB file access is single-writer).
  No module may spawn threads/processes without an ADR.
- *Typing:* mypy strict; public APIs use precise types (no `Any` escape hatches).

---

## epra.common (implemented — extension notes only)

| Module | Status | Extension points / notes |
|--------|--------|--------------------------|
| `config` | done | Add new config keys ⇒ extend the pydantic model + settings.yaml + a drift-guard test in the same commit. Never add a "misc" dict. `entsoe_token()` stays the only secret accessor. |
| `logging` | done | Ingestion passes `reports/ingestion/ingest_<date>.log` (EN-060). Do not add handlers elsewhere. |
| `timeutil` | done | The ONLY sanctioned TZ conversion outside dbt's `dim_calendar` (DM-011). New time helpers go here, never inline. |
| `db` | done | Analytics/strategies use `connect(settings, read_only=True)`. Writes to the warehouse happen only via dbt. |

---

## epra.ingest._io (new, internal — created by T1.01)

- **Purpose:** single writer for raw monthly parquet (ING-003/004/005).
- **Public (package-internal) API:**
  - `request_hash(url: str) -> str` — sha256 of URL with token param removed.
    *Pre:* url non-empty. *Post:* 64-hex; identical for identical token-stripped URLs. *Tests:* token stripped; stable.
  - `write_month(frame, dataset: str, month: date, request_hash: str, settings) -> Path`
    *Pre:* frame has `ts_utc` tz-aware UTC; all `ts_utc` within `month`. *Post:* file at §7 path; atomic replace; ING-004 columns appended. *Failure:* naive timestamps → `ValueError`; out-of-month rows → `ValueError` listing offenders. *Determinism:* fixed column order + writer options; data columns byte-stable. *Complexity:* O(rows). *Tests:* round-trip dtypes; atomicity; month-boundary rejection.
- **Failure modes / recovery:** disk full or partial write → temp file remains,
  target untouched; re-run overwrites cleanly. No retries here (I/O layer).
- **Metrics/logging:** one INFO per file: dataset, month, rows, path.
- **Performance:** ≤1 s per month file.
- **Extension:** new dataset = new `dataset` string + §7 contract row + contract test — no code change.

## epra.ingest._fetch (new, internal — created by T1.02)

- **Purpose:** cached, polite, retried acquisition of raw ENTSO-E XML (SG-01:
  `EntsoeRawClient`), reusable transport shape for GeoSphere JSON.
- **Public (package-internal) API:**
  - `fetch_entsoe(params: EntsoeQuery, settings, *, use_cache: bool = True) -> str`
    *Pre:* token available (raises the `entsoe_token()` RuntimeError otherwise). *Post:* XML text; cache file written on live fetch. *Failure:* 400/401/403 raise `IngestAuthError` with response body; exhausted retries raise `IngestTransportError`; Acknowledgement docs returned to caller for classification (parser decides per Appendix A). *Determinism:* cache path from `request_hash`. *Tests:* stub transport — retry/no-retry matrix, cache hit/miss, 7-day rule, `use_cache=False`, sleep called between live calls (mock clock), ING-008 log format, token absent from logs.
  - `EntsoeQuery` — frozen dataclass: document_type, domains, period_start/end (UTC), optional psr_type. *Invariant:* period_end > period_start; window ≤ 90 days (ING-030 enforced here).
- **Failure modes / recovery:** network flap → tenacity backoff (2→120 s, 6
  attempts); persistent failure → raise; caller never partial-writes a month.
- **Metrics/logging:** ING-008 line per request; cumulative request count at end of run.
- **Performance:** politeness-bound; backfill ≈ 4 datasets × ~90 quarterly chunks → runtime dominated by sleeps; keep chunk grouping quarterly (ING-030) to stay under ~45 min live backfill.
- **Extension:** circuit-breaker if ENTSO-E outage handling ever needed (ADR first).

## epra.ingest.entsoe (T1.04–T1.08)

- **Responsibilities:** dataset-specific query building, XML parsing (Appendix A),
  contract framing, window orchestration (`backfill`, `ingest_incremental`,
  `latest_complete_month`), CLI.
- **Internal API (pin these names; tests import them):**
  - `parse_publication_xml(xml: str) -> pd.DataFrame` (prices) — implements ING-050/060/063. *Post:* columns `ts_utc, price_eur_mwh, resolution, zone`; A03 fills applied + fill count attached as `frame.attrs["a03_fills"]`. *Failure:* non-EUR/MWH → `ContractError`; Acknowledgement for past window → `NoDataError`.
  - `parse_gl_xml(xml: str, kind: Literal["load","generation"]) -> pd.DataFrame` — ING-032 long format for generation; Appendix B mapping table `PSR_NAMES: dict[str, str]`.
  - `infer_resolution(ts: pd.Series) -> str` — spacing-based fallback (ING-060). *Test:* inference matches declared resolution on every fixture.
  - `iter_chunks(start: date, end: date) -> Iterator[tuple[date, date]]` — quarterly grouping of `timeutil.iter_month_starts`.
- **Data flow:** CLI/Make → window mgmt → per-chunk `_fetch` → parse → per-month split → `_io.write_month`.
- **Failure modes:** any month failing validation of its own frame aborts the run
  before writing that month (no partial months); previously written months stay.
- **Logging:** per-chunk INFO; per-month write INFO; A03 fill counts WARN if > 0.
- **Performance:** parse ≤ 2 s per quarterly chunk.
- **Testing:** every parser path fixture-covered (T1.03a list); zero network in tests (EN-070).
- **Extension:** a fifth dataset (e.g. hydro reservoir levels) = new query builder + §7 contract row + ADR (scope!).

## epra.ingest.geosphere (T2.02–T2.03)

- **Responsibilities:** station discovery (ING-091), daily-temperature ingestion
  (GeoJSON → §7 contract), politeness/cache via `_fetch`-shaped transport.
- **Key functions:** `discover_station(settings) -> StationInfo` (frozen dataclass:
  id, name, lat, lon, record_start) — *Post:* deterministic choice rule (name
  match "Graz", longest record, prefer "Graz Universität"); `parse_geojson(text) -> pd.DataFrame`
  — *Post:* `date, station_id, tl_mittel_c, parameter_raw`; missing days absent, never filled (A-2).
- **Failure modes:** dataset id missing → `DiscoveryError` listing available
  datasets (feeds the ADR); parameter renamed → same, via metadata endpoint.
- **Testing:** metadata + data GeoJSON fixtures; choice rule unit test with a
  crafted multi-station metadata fixture.
- **Extension:** second station (sensitivity) = config list + ADR; not planned (O-scope).

## epra.ingest.oespi (T2.04)

- **Responsibilities:** load + validate the reconciled manual CSV; expose a
  month-indexed frame (`month_local` first-of-month DATE, `oespi_base`,
  `oespi_peak`); ING-104 base-only mode.
- **Failure modes:** schema drift → `ContractError` naming columns; gate
  violations → `GateFailure` (from validate framework) — loader never "fixes" data (P-3).
- **Testing:** synthetic CSVs per gate fail case; real-CSV happy path post-T2.05.

## epra.ingest.calendar (T2.01)

- **Responsibilities:** hourly spine + local attributes + holiday/peak flags
  (ING-110); the ONLY module calling the `holidays` package.
- **Key function:** `build_calendar(settings, end: date | None) -> pd.DataFrame`
  — *Pre:* end ≥ window.start_date. *Post:* one row per UTC hour; DST days have
  23/25 local rows; columns exactly ING-110's list. *Determinism:* pure function
  of (config, end). *Complexity:* O(hours) ≈ 80k rows, < 5 s.
- **Testing:** ING-111 set + row-count properties + SG-10 subdiv assertion.

## epra.ingest.validate (T1.09, T2.03, T2.04)

- **Purpose:** ALL data-quality gates (SPEC-01 §§8–11) + the validation report.
- **Classes (the gate framework — used by every gated milestone):**
  - `GateResult` (frozen dataclass) — fields: `gate_id` (e.g. "ING-082"),
    `passed: bool`, `summary: str`, `evidence: pd.DataFrame | None`.
    *Invariant:* `gate_id` matches a SPEC REQ ID. *Lifecycle:* created by a gate
    function, aggregated, rendered, then discarded. *Tests:* rendering with/without evidence.
  - `ValidationReport` — collaborators: `GateResult`, markdown renderer.
    *Responsibilities:* aggregate results, render `reports/ingestion/validation_<date>.md`,
    compute overall pass/fail. *Invariant:* report lists every registered gate
    exactly once (no silent skips). *Error behavior:* `raise_if_failed()` raises
    `GateFailure` naming failing gate IDs (EN-061). *Tests:* all-pass, one-fail,
    skip-is-impossible.
- **Gate functions:** one per REQ ID, signature `gate_ing_082(prices_hourly: pd.DataFrame) -> GateResult`.
  *Pre:* input frame at documented grain. *Post:* pure — no mutation, no I/O.
  *Tests:* one passing + one failing synthetic case each (mandatory).
- **Recovery strategy:** none inside the module — a failed gate is a STOP signal
  for a human/agent investigation (AGENTS §2.2); the report is the evidence trail.
- **Extension:** M3+ gates live in dbt, NOT here — this module owns pre-warehouse gates only.

---

## epra.consumer.profile (T4.01–T4.04)

- **Responsibilities:** SPEC-03 algorithm; pure functional core (weights →
  normalize → frame) + thin imperative shell (read calendar, write parquet).
- **Internal API:**
  - `day_type(row) -> Literal["shutdown","weekend","weekday"]` — Step 2
    precedence; *Tests:* each precedence rule + Christmas/holiday collisions.
  - `special_factor(date_local, cfg) -> float` — maintenance vs shutdown vs 1.0;
    SG-04 first-Monday rule; *Tests:* Aug-1-Monday year; non-maintenance August day.
  - `hourly_weights(calendar_df, cfg) -> pd.Series` — Steps 1–4 composed.
  - `normalize_by_local_year(weights, calendar_df, cfg) -> pd.Series` — LP-004 +
    LP-034 hypothetical-year rule. *Post:* every full local year sums to
    `annual_consumption_mwh` ± 1e-9 internally (±0.01 is the gate, not the target).
  - `build_profile(calendar_df, cfg) -> pd.DataFrame` — orchestrates; *Post:*
    `ts_utc, load_mwh`, every calendar hour exactly once, no NaN/negatives.
- **Failure modes:** calendar not covering the requested window → `ValueError`
  (never silently truncate); unknown `profile_name` behavior → only
  `styriametal_v1` and `flat_baseload` accepted (LP-030), else `ValueError`.
- **Performance:** vectorized pandas; full window < 10 s. No Python-level per-hour loops.
- **Reproducibility:** bit-stable ⇒ avoid float nondeterminism: single-threaded
  numpy ops only; goldens pin the result (LP-040 sha256).
- **Extension:** new profile = new YAML file + ADR; the engine must not grow
  profile-specific branches (config-driven only, LP-002).

---

## epra.analytics.* (T5.01–T5.07)

Shared contract for `descriptive`, `spread`, `regimes`, `weather`:

- **Shape:** each module = `run(settings) -> None` orchestrator + pure
  computation functions returning frames/figures; artifacts written only via the
  shared kit (T5.01) so RP-701/702 styling and AN-704 prose sections are uniform.
- **Inputs:** marts via `db.connect(read_only=True)`; never raw/staging (AN preamble).
- **Outputs:** exactly the SPEC-04 §6 artifact list + SSOT input rows (VERIFIED).
- **Failure modes:** missing mart/empty result → raise with the SQL that
  returned empty (a mart gap is an upstream bug, never worked around here).
- **Determinism:** `regimes` is the only stochastic module — seeds fixed
  (42..51 restarts); numpy single-threaded; AN-705 ×2 identity is the test.
- **Performance:** full `make analyze` < 5 min.
- **Metrics:** each module logs artifact paths + SSOT keys emitted.
- **Testing:** computation functions unit-tested on synthetic frames (crafted to
  make expected values hand-computable); chart functions object-inspected (title,
  axis labels with units, source note, tag stamp present); prose length gate test (AN-704).
- **Extension:** a fifth analytics block is out of scope (Charter §4.2) — extend
  only via Charter change.

Key function pins:
- `descriptive.annual_summary(prices_hourly) -> pd.DataFrame` — AN-101 columns; *Test:* synthetic year with known mean/median/negatives.
- `spread.spread_stats(at, delu, calendar) -> pd.DataFrame` — AN-202; *Test:* constructed spread with known peak/off-peak split.
- `regimes.fit_hmm(dt_std: np.ndarray) -> HmmFit` — `HmmFit` frozen dataclass
  (model params, state_sequence, state_order_by_std, log_likelihood, restart_seed_used).
  *Invariant:* labels remapped so state 0 = calm (lowest std). *Tests:* determinism; label ordering on synthetic 3-regime data.
- `regimes.december_regime(year) -> Literal["calm","elevated","crisis"]` — feeds
  ST-401 step 4; *Post:* derived from majority state of that December's days; pin
  this definition (SG note in doc 14 → adopted rule).
- `weather.fit_load_hdd(daily) -> OlsSummary` — HC1 SE, month FE; *Test:* synthetic linear data recovers slope.

---

## epra.strategies.* (T6.01–T6.10)

- **Architecture:** functional core — cost engines are pure functions over
  pre-aligned frames; imperative shell handles DuckDB reads and parquet writes
  (ST-001). No strategy class hierarchy: strategies are **rows in config +
  functions**, selected by id (Strategy pattern via dispatch table, see
  [08_PATTERNS.md](08_PATTERNS.md)).
- **Classes:**
  - `Anchors` (frozen dataclass): `p_ref_base, p_ref_peak, oespi_base_ref,
    oespi_peak_ref`. *Invariant:* all > 0; `p_ref_peak ≥ p_ref_base` (peak power
    costs more in 2019 — assert; if real data violates this, that is a STOP-and-
    investigate, not an assert removal). *Tests:* synthetic-2019 exact values.
  - `AlignedVolumes` (frozen dataclass): monthly volumes + hourly load with
    NULL-price hours dropped (ST-101). *Invariant:* identical monthly volume
    across strategies by construction.
- **Key function contracts:**
  - `retrospective.cost_s1(hourly: pd.DataFrame) -> pd.DataFrame` — *Pre:* hourly
    has load_mwh + price, no NULLs (alignment already applied). *Post:* monthly
    rows; `cost_eur = Σ load×price` exact to float64. *Test:* hand-computed month.
  - `retrospective.p_s2(month, oespi, anchors, w_peak) -> float` — ST-102 formula
    verbatim; *Test:* algebraic identity at ÖSPI = ref values ⇒ p_S2 = blended p_ref.
  - `retrospective.p_s3(year, oespi, anchors, cfg) -> float` — lock-window mean +
    premium; *Failure:* lock window months missing from ÖSPI → raise (never
    extrapolate, A-2). *Test:* no-lookahead (ST-503) + at-ref identity + premium sensitivity.
  - `forward_risk.build_cost_cells(...) -> CostCells` — precompute
    (calendar_month × pool_year × strategy) monthly costs (ST-406). *Post:* cell
    count = 12 × pool_years × 7; each cell reproducible independently. *Test:*
    cell values equal direct per-path computation on a 2-month toy (equivalence).
  - `forward_risk.simulate(cells, rng_seed, n_paths, pool) -> pd.DataFrame` —
    single `default_rng(seed)`; draw order: path-major, month-minor (pin it);
    *Post:* per-strategy annual totals, n_paths rows. *Tests:* determinism ×2;
    P5≤P50≤P95 ordering; pool restriction (no-crisis) uses only allowed years.
  - `forward_risk.summarize(paths) -> pd.DataFrame` — mean/std/P5/P50/P95/CVaR95
    per SG-08 method pins. *Test:* closed-form check on a crafted distribution.
- **Failure modes:** ÖSPI coverage gap in a drawn/lock month → raise before
  simulating (EN-083 suppression is the *refresh workflow's* decision, not a
  silent engine behavior).
- **Performance:** ST-406 budget — cells < 60 s, simulation < 60 s, total
  `make simulate` < 10 min with margin.
- **Reproducibility:** seed + draw order + float64 accumulation order pinned ⇒
  SSOT-identical reruns (ST-405).
- **Extension:** new hybrid ratio = config change + dim_strategy seed row +
  goldens regeneration (ADR + O-7 check: stays within the 4 families).

---

## epra.report.* (charts: T7.02; format/style: done)

- `charts` responsibilities: executive PNGs only (RP-201..204); every figure
  built through a single `new_figure()/finalize(fig, *, title, tag, source)` pair
  from the T5.01 kit (uniformity is the point); RP-301 reproducibility test reads
  the CSV exports, not internal frames.
- Failure modes: missing SSOT/exports inputs → raise listing the missing file
  and which task produces it.
- Testing: object inspection (no image snapshots — font rendering varies across
  OS; see [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) §charts).

## scripts/ (thin shells only)

| Script | Contract owner | Notes |
|--------|----------------|-------|
| `generate_ssot.py` | T6.08 | Reads outputs, never recomputes; all logic importable (`scripts/` shells call functions in `epra/` where testability demands it — SSOT assembly logic lives in `epra.report.ssot` (new module, same contract) so it's unit-testable under coverage). |
| `check_ssot_consistency.py` | T6.09 | Same split: parsing/matching logic in `epra.report.ssot_check`, script = CLI shell. |
| `export_marts.py` | T7.01 | Pure mart→CSV dump; schemas contract-tested (DM-070). |
| `bootstrap_fixture_warehouse.py` | T3.06 | CI-only; builds data/raw from fixtures; must never run against a populated data/ dir without `--force`. |
| `generate_golden_metrics.py` | T6.10 | Writes goldens; refuses to run if git tree dirty (protects EN-072 review flow). |
| `oespi_reconcile.py` | done | — |
| `check_no_token_in_code.py` | done | — |
