# 05 — IMPLEMENTATION GUIDES (the "how", per milestone)

Not code — decisions, gotchas, worked micro-examples, and investigation
protocols. Read the relevant section in the same session as the task.

---

## 5.1 M1 — ENTSO-E

### Client strategy (SG-01, adopt via ADR in T1.02's commit range)
Use `EntsoeRawClient` (returns raw XML strings) so ING-009's *raw response*
cache is honored literally, then parse with our own Appendix-A parser (T1.04).
Do NOT use `EntsoePandasClient` for persistence: its parsed frames hide
`resolution`, `curveType`, and currency fields the contracts need, and its
timezone behavior varies by version (T-4). entsoe-py remains the query-URL
builder + transport; our parser is the contract owner. If `EntsoeRawClient`
proves unusable, Appendix A raw REST is the sanctioned fallback (ADR).

### Chunking loop shape
Iterate `iter_month_starts(2019-01-01, end)`, group into calendar quarters,
one request per quarter per dataset (ING-030's ≤90-day bound holds; Q1 2024 =
91 days — use months 1–3 grouping but verify day count ≤ 92 is acceptable:
it is NOT ≤ 90, so group Jan–Feb–Mar as **two requests (Jan–Feb, Mar)** in leap
years, or simply request month-by-month — month-by-month is simpler, still only
~90 requests/dataset ≈ 45 s of sleeps; **decide: month-by-month**, note in ADR
with SG-01).

### Timezone recipe (T-1/T-4, do exactly this)
Request boundaries: build `pd.Timestamp(month_start, tz="Europe/Vienna")`.
Parse: period `timeInterval/start` is UTC in the XML — construct `ts_utc`
directly from it; never localize. Persist µs-UTC. The DST fixtures make any
deviation fail loudly.

### A03 forward-fill (ING-063)
Fill *within the period only*, count fills, attach to `frame.attrs`, log WARN,
surface count in the validation report. The hour-coverage gate (ING-080)
independently re-checks totals — do not let the parser's fill count feed the
gate (independence is the point).

### ING-082 failure investigation protocol (do IN ORDER, stop when found)
1. Unit sanity: is the annual mean off by ~×1000 (kWh/MWh) or ~×100? → parser unit bug.
2. TZ shift: does the mean move when you shift ts by ±1/±2 h? → localization bug.
3. Coverage: missing winter/summer months skew the mean → check ING-080 first.
4. Zone mix-up: AT vs DE_LU swapped → compare a known crisis month (2022-08 AT
   base ≈ 400–550 EUR/MWh region; DE lower).
5. Only after 1–4: consider whether the gate range itself is wrong → ADR + owner.

### Live backfill runbook (T1.10)
Dry-run one month first (`--start 2024-01-01 --end 2024-01-31`), eyeball the
parquet, then full backfill. Expect O(4×90) requests ≈ several minutes of
sleeps + transfer. Then `make validate-ingest`; commit the report; spot-check
2022 annual mean lands in 200–320.

---

## 5.2 M2 — Auxiliary data

- **Calendar first** — everything else in the repo eventually joins it.
  `holidays.country_holidays("AT", subdiv="6")` is the expected call (SG-10);
  assert in a test which subdiv code yields Styrian holidays; the `holidays`
  pin (>=0.50) uses ISO codes ("6" = Steiermark).
- **GeoSphere:** run discovery against the live metadata endpoint (no auth, no
  token needed) — do it early; the ADR captures the JSON evidence. Resource
  endpoint returns GeoJSON: `features[0].properties.parameters.tl_mittel.data`
  aligned with `timestamps` — verify against the fixture you record.
- **ÖSPI transcription protocol (human):** use the CURRENT-method series if it
  reaches back to 2019-01 (ING-102); transcribe Base and Peak columns for every
  month; enter `source_url` + `retrieved_at` per row; do entry1 and entry2 in
  separate sittings (or one human + one agent-read of the PDF); never "correct"
  during reconciliation without re-opening the source (A-2).

---

## 5.3 M3 — dbt warehouse

- **Schema naming (SG-13):** dbt's default `generate_schema_name` prefixes the
  target schema (`main_staging`). Add the standard override macro so custom
  schemas are used literally — otherwise the M3 schema contract test can never
  pass. This is the #1 known dbt-duckdb trip-wire.
- **External sources:** define each raw dataset once in `sources.yml` with
  `meta.external_location: "read_parquet('../data/raw/<ds>/**/*.parquet')"` (or
  a staging model using `read_parquet` directly — pick ONE mechanism repo-wide;
  the contract is DM-004's "defined once").
- **15-min aggregation (T-2):** `avg(price) group by time_bucket/hour-trunc of
  ts_utc` — mean, never sum; `n_subhours` = `count(*)`; add the fixture month
  with mixed PT60M/PT15M days.
- **Stand-ins (SG-06):** fixture bootstrap writes tiny
  `consumer_load_hourly.parquet` / `strategy_costs_monthly.parquet` so
  `dbt build` is green in CI before M4/M6; locally, M4/M6 replace them with real
  files. Never gate M3 on downstream milestones.
- **Contract YAML:** generate `dbt/contracts/marts_contract.yml` by querying
  `information_schema.columns` once the marts match SPEC-02 §5, review by hand
  against the spec tables, commit; the test then diffs live vs committed.

## 5.4 M4 — Consumer profile

Worked example to validate intuition (not a test): weekday hour 14 in March:
`w = 1.00 (day shape) × 1.02 (March) × 1.0 (no special) = 1.02`. Sunday 03:00 in
July during no special window: `0.30 × 0.95 = 0.285`. Ratio weekday-14/Sunday-03
across the year lands in LP-040's [2.8, 3.6] band by construction. If your ratio
is ~1.0 you applied day shapes to the wrong axis; if ~10 you multiplied factors
twice.

Christmas rule precision: Dec 24–31 belong to year Y's normalization, Jan 1 to
Y+1 (LP §3.3); day_type is `shutdown` for all nine days; `special_factor` = 1.0
(shutdown shape already dampens — "no double dampening").

Partial forward year (LP-034): compute Σw over the *hypothetical full* final
local year (calendar rules extend beyond the profile window), scale by
`annual/Σw_full`, emit only the hours inside the window. Test equality of
overlapping monthly volumes with a full-year run.

## 5.5 M5 — Analytics

- **d_t series** built once (regimes module owns it; GARCH imports the same
  function): daily base price → `diff()` → drop first NaN. Arithmetic diffs
  (T-3): never log-transform.
- **HMM determinism (RB-11):** set `OMP_NUM_THREADS=1` style single-threading
  is NOT needed for hmmlearn (pure numpy EM), but pin restarts 42..51 and select
  max LL with deterministic tie-break (lowest seed wins ties — pin it). Persist
  the chosen seed in the stats table for the record.
- **December regime for ST-401 step 4:** majority vote of that December's daily
  states; ties → the higher-volatility state (conservative). Record per-year
  labels in a small parquet consumed by forward_risk (data interface, not import).
- **GARCH rescale:** if `arch` warns about scale, multiply d_t by 0.1, note the
  rescale in the output md, report persistence α+β unchanged (scale-invariant).

## 5.6 M6 — Strategies

### Anchor identity checks (cheap unit tests that catch T-5 dead)
At `oespi == oespi_ref` the S2 price collapses to
`p_ref_base(1−w) + p_ref_peak·w` — assert this algebraic identity. S3 at ref
index + premium 0 equals the same blend. If real S3 2021 lands near ~50–80
EUR/MWh you're sane; ~5000 means index×volume (T-5).

### Bootstrap vectorization equivalence (why ST-406 is exact)
Annual path cost = Σ over months of cost(month, drawn_year, strategy). Costs
are additive over months, and within one path each month's draw is independent
of other months' draws given the pool. Therefore precomputing
`cell[c, y′, s] = cost of calendar month c under historical year y′ for strategy s`
and summing 12 lookups per path is *identical* to per-path recomputation —
provided S3's lock price inside a path uses: real ÖSPI where the lock window is
observed; drawn ÖSPI where it is simulated (ST-402). Implementation: for the
next-12-month horizon the lock window (H2 of prior year) is fully in the past ⇒
p_S3 is a constant per path-set; assert this at runtime and keep the drawn-ÖSPI
branch implemented for horizon extensions but tested via synthetic horizon.

### Draw order pin (ST-405 depends on it)
`for path in range(n_paths): for month in horizon_months: draw`. One RNG. Never
draw month-major; never re-seed inside loops.

### SSOT generator design
Producers (profile, analytics, strategies) each persist a typed
`ssot_inputs_<producer>.parquet` (key, value, unit, tag, produced_by). The
generator concatenates, validates (GV-302 key set complete, no duplicate keys,
E-2: no VERIFIED row produced by a module that declares CALIBRATED inputs),
sorts by key, renders markdown. `updated_at` = max source-file mtime rendered
ISO — deterministic given artifacts (SG-09 companion).

### Consistency checker design (GV-303)
Tokenize README/EXEC_SUMMARY for `number + unit` bigrams (units: EUR, EUR/MWh,
%, hours, M); for each, find an SSOT row whose value rounds (half-up, to the
displayed decimals) to the literal; unmatched → error listing candidates;
whitelist file for years/section refs with mandatory `# reason` per line.
Mutation-test it (change a digit → must fail).

## 5.7 M7 — Reporting & release

- RP-201 bar values = `wrong_strategy_cost_<year>` from the exports CSV — the
  RP-301 pytest recomputes max−min per year from `strategy_annual_summary.csv`
  and asserts chart-input equality.
- README rewrite: keep the M0 skeleton's structure (it already matches §6);
  replace status/pending blocks with SSOT-quoted numbers + tags.
- refresh.yml: job steps = checkout → setup-uv → `make refresh` (token from
  secret) → upload artifacts → ÖSPI-coverage check (if latest complete month not
  in `oespi_monthly.csv`, add PR-body warning + suppress strategy outputs for
  that month per EN-083) → create-pull-request action with path filter on
  committed report files; skip cleanly when diff is empty (SG-18).
- DL-1 rehearsal: fresh clone into a temp dir, `.env` with token, `make setup
  && make backfill && make all`, assert every DL artifact exists — this is the
  release gate's first row, done for real, not simulated.
