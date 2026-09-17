# Phase 6: M5 Analytics - Research

**Researched:** 2026-09-02
**Domain:** Read-only DuckDB marts → SPEC-04 A1/A2/A4/A3 artifacts (md/png) + VERIFIED SSOT producer parquet; seeded HMM + GARCH; matplotlib RP-701/702
**Confidence:** HIGH for in-repo marts/style/stubs (read this session). HIGH for hmmlearn/arch already pinned in `pyproject.toml`. MEDIUM for AN-304 on real data (this checkout has no warehouse — gate is skip-if-incomplete per D-06).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `run(settings)` reads marts only; unit tests inject frames.
- **D-02:** Shared `_kit.py` writers; object-inspect charts, no image diff.
- **D-03:** `ssot_inputs_analytics.parquet` columns `key, value, unit, tag, produced_by`; tag VERIFIED.
- **D-04:** `python -m epra.analytics` A1→A2→A4→A3; `make analyze` does not invoke dbt.
- **D-05:** No committed fixture PNGs.
- **D-06:** AN-304 skip if 2019 / crisis window incomplete; fail closed when coverage exists; no fixture extension; no gate widening.
- **D-07:** Heatmap 5 panels; missing year empty.
- **D-08:** Duration-curve 2022 = crisis styling (Okabe-Ito vermillion).
- **D-09:** HMM spec pins + BLAS 1-thread; equal-LL → lower seed.
- **D-10:** `december_regime` = December majority state (M5 implements, M6 consumes).
- **D-11:** GARCH rescale /10 only on scale warning; never clamp α+β.
- **D-12:** No speculative ADR-014.
- **D-13:** Market charts VERIFIED; A4 invariance sentence; no LP-050 on A1–A3.
- **D-14:** ADR only if AN-304/HMM fails after two focused attempts.

### Deferred
- `NUMERIC_SSOT.md`, ST-401 consumers of `december_regime`, executive charts, TP.02, EN-072.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ANA-01 / REQ-Q2 | A1–A4 + AN-304 + §6 files | Patterns 1–7 |
| AN-304 | ≥70% crisis-window days in top-2 states; ≥60% of 2019 calm | Pattern 5 + D-06 skip |
| AN-701..705 | existence, gate, VERIFIED SSOT, ≥400-char prose, ×2 SSOT identity | Pattern 7 + Validation map |
</phase_requirements>

## Summary

M5 is **mart-backed reporting**, not ingestion. `fct_price_hourly` already has AT/DE-LU prices, `load_at_mw`, `is_peak_hour`, `year_local`/`hour_local`/`is_weekend`, `hdd_18` (SG-05). `fct_price_daily` has `price_base_eur_mwh` + `hdd_18` for A3 `d_t` and A4. Style constants (`FIGSIZE`, `DPI`, `SOURCE_NOTE`, `OKABE_ITO`) exist in `epra.report.style`. `hmmlearn` and `arch` are already dependencies.

Non-obvious HOW items:

1. **Base / peak / off-peak from hourly mart:** there is no separate `price_base` column on `fct_price_hourly`. **Base** = all hours' `price_at_eur_mwh`; **peak** = rows with `is_peak_hour`; **off-peak** = not peak. Peak−off-peak spread is mean(peak) − mean(off-peak) per year (and hourly peak−off-peak is not a per-hour column — AN-101 is annual aggregates).
2. **NULL prices on the calendar spine:** `fct_price_hourly` left-joins onto `dim_calendar`, so some hours may have NULL `price_at_eur_mwh`. Analytics must **drop NULL-priced hours** for price stats (do not treat NULL as 0). Log/count dropped hours in A1 md. Same for DE-LU when computing spread.
3. **A3 `d_t`:** daily first difference of `fct_price_daily.price_base_eur_mwh` ordered by `date_local` (not UTC date). Arithmetic, not log (T-3). Drop the first day and any day whose base is NULL.
4. **AN-304 vs fixture:** ADR-010 window 2022–2024 has **no 2019**. D-06 skip is mandatory. Real-data gate remains the M5 ROADMAP SC#2.
5. **Determinism:** pin BLAS threads inside `fit_hmm` *before* constructing `GaussianHMM`. HMM `random_state` is the restart seed. Do not set global numpy seed for A1–A4 (they are deterministic without RNG).
6. **Shared kit:** one writer for SSOT rows (append-all-then-atomic-replace, like profile). PNG: `fig.savefig(..., dpi=DPI, bbox_inches="tight")` after RP-702 annotations via `fig.text`.

**Primary recommendation:** T5.01 kit + `__main__` first; then A1, A2, A4 in parallel-safe plans (all depend only on kit); A3 HMM then GARCH; T5.07 Makefile + AN-70x + BUILD_LOG.

## Architectural Responsibility Map

| Capability | Primary | Secondary | Rationale |
|------------|---------|-----------|-----------|
| Mart SQL → DataFrame | `_kit.load_price_hourly` etc. | `epra.common.db.connect` | AN preamble |
| Tables / PNG / SSOT rows | `_kit` writers | `report.style` / `report.format` | RP-701..703 |
| A1–A4 domain | respective modules | kit I/O only | SPEC-04 blocks |
| HMM/GARCH | `regimes.py` | `d_t` helper shared by T5.05/T5.06 | T-3, AN-302/303 |
| Operator | `python -m epra.analytics` | Makefile `analyze:` | EN-050 |
| AN-304 | `regimes.check_an304` | skip vs fail (D-06) | M5 exit |

## Standard Stack

| Library | Already pinned | Use |
|---------|----------------|-----|
| duckdb + `epra.common.db` | yes | read-only marts |
| pandas / numpy | yes | aggregates, `d_t`, checksums |
| matplotlib | yes (report charts stub uses it) | Agg backend, RP-701 |
| statsmodels | yes (`pyproject` ignore for mypy) | OLS HC1 month FE |
| hmmlearn | `hmmlearn>=0.3` | GaussianHMM |
| arch | `arch>=7` | GARCH(1,1) |
| threadpoolctl or os.environ | stdlib env is enough | D-09 |

**No new packages.** Do not add seaborn (RP-701).

### Alternatives considered
- **sklearn HMM:** spec names `hmmlearn`.
- **PyMC / extra Bayesian vol:** Charter §4.2 / A-3.
- **Image-hash golden PNGs:** flaky; D-02 object inspection.

## Architecture Patterns (see 06-PATTERNS.md)

1. Kit: connect + SQL named in errors + PNG/md/SSOT writers
2. A1 annual_summary on synthetic years
3. A2 spread_stats + axhline(0)
4. A4 OLS month FE HC1; never recompute HDD
5. A3 `d_t` + fit_hmm + AN-304 skip
6. GARCH persistence identity
7. `__main__` + Makefile + wipe 12 filenames

## Common Pitfalls

1. **Log returns** — T-3; negative prices exist (AN-104).
2. **NULL hours as zero** — spine left-join; dropna on price columns.
3. **UTC year for AN-101** — use `year_local`.
4. **Recomputing HDD** — use `hdd_18` from marts.
5. **AN-304 false pass on skip** — skip ≠ pass; `make analyze` must still fail closed on real data.
6. **Committing fixture heatmaps** — A-2 / D-05.
7. **Multi-thread BLAS HMM** — AN-705 flake (RB-11).
8. **Clamping α+β** — forbidden.
9. **Seaborn** — RP-701.
10. **Invoking dbt from analyze** — D-04.

## Validation Architecture

See `06-VALIDATION.md`. Sampling: after each plan, `pytest tests/unit/test_analytics*.py`; after T5.07, `make lint && pytest -m "not live"`; AN-304 on real warehouse is operator/SC#2.

## Security

No tokens. No network. Read-only DuckDB. Do not log SQL with credentials (there are none).
