# Phase 5: M4 Consumer Profile - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-02
**Phase:** 5-M4 Consumer Profile
**Areas discussed:** Calendar input, special-window rules, peak share → SSOT, flat_baseload config, golden checksum, stand-in replacement
**Mode:** `/gsd-discuss-phase 5 --auto` (recommended options selected)

---

## Calendar input

**Q1 — What does `build_profile(calendar_df, cfg)` receive as `calendar_df`?**

| Option | Description | Selected |
|--------|-------------|----------|
| ING-110 calendar frame / parquet | Columns from `build_calendar()` / `data/raw/calendar/calendar.parquet`; tests call the existing builder with a fixed `end`; no DuckDB, no weather | ✓ |
| DuckDB `marts.dim_calendar` | Join warehouse; pulls unused weather/season/HDD; couples M4 tests to a built duckdb | |
| Rebuild local attributes in profile.py | Re-derive holiday/peak/dow from `ts_utc` — duplicates ING-110 and violates "calendar is the spine" | |

**User's choice:** ING-110 calendar frame (Recommended).
**Notes:** `is_peak_hour` on the calendar is already ADR-011 holiday-aware; LP-020 reuses it rather than re-coding Mon–Fri 08–20.

---

## Special-window rules

**Q1 — How is "first full Mon–Sun week of August" resolved when 1 August is a Monday (SG-04)?**

| Option | Description | Selected |
|--------|-------------|----------|
| SG-04 as written → ADR-012 | first Monday `m ≥ Aug 1`; window `[m, m+6]`; 1 Aug Monday → 1–7 Aug; test year 2022 | ✓ |
| Require a full week strictly inside August starting the first Monday *after* Aug 1 | Would skip 1–7 Aug when Aug 1 is Monday; contradicts the proposed gap resolution | |
| ISO-week of August that is "week 1" | Ambiguous around month boundaries; not the spec's Mon–Sun wording | |

**User's choice:** SG-04 via ADR-012 (Recommended).

**Q2 — Where does Christmas `shutdown_factor = 1.0` live (LP-002 vs §6 verbatim YAML)?**

| Option | Description | Selected |
|--------|-------------|----------|
| Identity rule, YAML unchanged | 1.0 means no extra dampening on top of the shutdown *shape*; do not add a key to frozen §6 YAML; do not hardcode 0.18/0.60/1.06 | ✓ |
| Add `shutdown_factor: 1.0` to YAML | Makes LP-002 literal but mutates the authoritative §6 copy already committed verbatim | |
| Hardcode `0.18` shutdown shape in Python | Violates LP-002 and T4.01 grep AC | |

**User's choice:** Identity rule, YAML unchanged (Recommended).

---

## Peak share → SSOT

**Q1 — Which year's peak share is the single SSOT value (SG-03)?**

| Option | Description | Selected |
|--------|-------------|----------|
| 2019 reference year + <1 pp yearly-deviation test → ADR-013 | Matches all other 2019 anchors; escalate if deviation ≥ 1 pp | ✓ |
| Mean of complete years | Invents a blended number not named in the gap proposal | |
| Latest complete year | Moves every refresh; breaks ST-102 stability | |

**User's choice:** 2019 + deviation test via ADR-013 (Recommended).

**Q2 — Where is the SSOT-input parquet written?**

| Option | Description | Selected |
|--------|-------------|----------|
| `data/processed/ssot_inputs_profile.parquet` (`key, value, unit, tag, produced_by`) | Matches implementation guide §5.6 producer-file pattern; M6 concatenates | ✓ |
| Append rows to a shared `reports/ssot_inputs.parquet` now | Races with M5/M6 producers; no generator yet | |
| Defer the file to M6 | Leaves T4.03 AC (`consumer_peak_share` ready for SSOT) unmet | |

**User's choice:** `ssot_inputs_profile.parquet` (Recommended).

---

## flat_baseload

**Q1 — How is LP-030 configured, given 03_MODULES says "new YAML file"?**

| Option | Description | Selected |
|--------|-------------|----------|
| Same function / CLI `--profile`; all weights 1.0; no second YAML | SPEC-03 §5 is the authority (A-1); 03_MODULES extension note is non-binding until ADR | ✓ |
| Second YAML `config/consumer_profile_flat.yaml` | Matches 03_MODULES wording but contradicts SPEC-03 §5 "same function with profile_name" | |
| Separate `build_flat_profile()` | Duplicates normalization; forked code paths | |

**User's choice:** Same function, no second YAML (Recommended).
**Notes:** Unknown names raise `ValueError`; only `styriametal_v1` and `flat_baseload`.

---

## Golden checksum

**Q1 — When is `tests/golden/consumer_load_2023.sha256` created?**

| Option | Description | Selected |
|--------|-------------|----------|
| Commit on first green LP-040 in the T4.04 PR | Bit-stability from day one; EN-072 regeneration stays a human stop | ✓ |
| CI writes the file if missing | Non-deterministic first CI run; golden not reviewed | |
| Skip persisting until a later "stabilize" PR | LP-040's "assert it thereafter" never starts | |

**User's choice:** Commit in T4.04 PR (Recommended).

---

## Stand-in replacement & Makefile

**Q1 — How does `fct_consumer_load_hourly` start reading the real SPEC-03 file?**

| Option | Description | Selected |
|--------|-------------|----------|
| Single LP-003 parquet + sources.yml path change + bootstrap writes the same path; `all:` reorders to profile then transform | Literal LP-003 path; CI still has a stand-in until `make profile` runs; warehouse never sees stand-in on `make all` | ✓ |
| Keep monthly `write_month` partitions under `consumer_load_hourly/**` | Deviates from LP-003's named file; would need an ADR | |
| `make profile` also runs `dbt build --select fct_consumer_load_hourly+` | Mixes M4 write with M3 transform; breaks the two-step ingest/validate precedent | |

**User's choice:** Single file + sources.yml + `all:` reorder (Recommended).
**Notes:** Procurement stand-in layout unchanged. `make profile` does not invoke dbt.

**Q2 — LP-050 / LP-051 this milestone?**

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm LIMITATIONS §1 (LP-051); defer LP-050 captions to M5/M7 artifacts | §1 already has the required sentence; no consumer-load charts exist yet | ✓ |
| Add LP-050 captions to parquet metadata | Parquet is not a reader-facing artifact; over-implements | |

**User's choice:** Confirm LP-051 only (Recommended).

---

## Claude's Discretion

- Vectorized pandas/numpy; pinned 03_MODULES function names; ~60-line functions (W-3).
- CLI extras (`--end`, output overrides) and atomic processed-parquet write pattern.
- Checksum encoding details (stable `ts_utc` order + float64 bytes vs canonical parquet digest).
- How monthly volumes attach `year_local`/`month_local` (must match LP-021 grain).

## Deferred Ideas

- LP-050 captions on charts/README → M5/M7.
- `generate_ssot.py` / NUMERIC_SSOT.md → M6.
- Procurement stand-in replacement → M6.
- TP.02 GitHub required check → operator.
- Third named load shape → out of scope (A-3).
