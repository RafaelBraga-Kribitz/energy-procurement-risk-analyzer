# SPEC-08 — Governance & Quality (deliberately lightweight)

Requirement IDs: `GV-xxx`. Design constraint from the Charter (§4.2 O-5): governance
weight ≈ 30% of the decision-analytics-reconstruction repo. The three mechanisms below
are ALL the governance there is. Do not add more.

---

## 1. Epistemic tags

- GV-101: Tags and rules as defined in Charter §5 (VERIFIED / CALIBRATED / SIMULATED).
- GV-102: Implementation: every SSOT row carries a `tag` column; chart captions carry the
  tag when CALIBRATED/SIMULATED content is displayed (RP-702).

## 2. ADRs (Architecture Decision Records)

- GV-201: Location `docs/ADR/`, filename `ADR-NNN_short-title.md`, append-only (never
  edit a merged ADR; supersede with a new one referencing the old).
- GV-202: Template (verbatim):

  ```markdown
  # ADR-NNN: <title>
  Date: YYYY-MM-DD  |  Status: accepted | superseded-by ADR-MMM
  ## Context
  ## Decision
  ## Consequences
  ## Spec deviations (list REQ IDs affected, or "none")
  ```

- GV-203: ADR triggers (mandatory, from the specs): charter change; spec deviation forced
  by external reality; new dependency; gate widening; ÖSPI series/method choice (ING-102);
  GeoSphere substitutions (ING-091/092); golden regeneration rationale may reference its
  PR instead of an ADR.

## 3. SSOT mechanism

- GV-301: `reports/NUMERIC_SSOT.md` is generated ONLY by `scripts/generate_ssot.py`,
  which reads computed parquet/DuckDB outputs and writes a single markdown table:
  `key | value | unit | tag | produced_by | updated_at`.
- GV-302: Minimum key set: `wrong_strategy_cost_total`, `wrong_strategy_cost_<year>` ×5,
  `best_strategy_5yr`, `cost_<strategy>_<year>` matrix, `p95_next12m_<strategy>`,
  `cvar95_next12m_<strategy>`, `p_ref_base`, `p_ref_peak`, `oespi_base_ref`,
  `consumer_peak_share`, `annual_mean_price_<year>`, `neg_hours_<year>`,
  `spread_mean_<year>`, `garch_persistence`, `data_last_month`.
- GV-303: `scripts/check_ssot_consistency.py` (CI-required): parses README.md and
  reports/EXEC_SUMMARY.md for numeric literals adjacent to SSOT units (EUR, EUR/MWh, %,
  hours, M) and verifies each matches an SSOT value within rounding documented in the
  script (README may round; SSOT holds full precision). Whitelist file
  `scripts/ssot_whitelist.txt` for non-result numerics (years, section numbers, config
  echoes); every whitelist entry needs an inline comment saying why.

## 4. CI gates summary (defined in SPEC-07 §8; listed here as the quality contract)

lint → tests+coverage → dbt fixture build → SSOT consistency. A PR that touches results
must include regenerated SSOT in the same PR (checked by ssot freshness: `updated_at`
newer than the newest modified results file).

## 5. Data quality gates index (where they live)

| Domain | Gate IDs | Spec |
|--------|---------|------|
| ENTSO-E ingestion | ING-080…085 | SPEC-01 §8 |
| GeoSphere | ING-094 | SPEC-01 §9 |
| ÖSPI | ING-101, ING-103 | SPEC-01 §10 |
| dbt models | DM-060…066 | SPEC-02 §6 |
| Load profile | LP-040…042 | SPEC-03 §7 |
| Analytics | AN-701…705 | SPEC-04 §7 |
| Strategies | ST-601…604 | SPEC-05 §9 |

## 6. LIMITATIONS.md (must contain at least these sections, honestly written)

1. Consumer load profile is constructed, not measured (LP-051 wording), plus the
   flat-baseload sensitivity result.
2. ÖSPI as forward/contract proxy: what it captures, what it misses (individual supplier
   margins, credit terms, volume flexibility clauses); direction of likely bias unknown —
   say so.
3. Fixed premium (5 EUR/MWh) is an assumption; show the 0/10 sensitivity numbers.
4. Bootstrap risk simulates from history 2019→present; a regime with no historical
   precedent is outside the model. The no-crisis conditional variant partially addresses,
   does not solve, this.
5. Grid fees/taxes/levies excluded: procurement-decision scope only; total bill impact
   differs.
6. 2025 data caveats if any gates required investigation.
7. No forecast-skill claim anywhere (restate O-1).

## 7. What deliberately does NOT exist here

No audit-finding registry, no session handouts, no re-verification matrix, no numbered
finding IDs, no governance CI workflow beyond §4. If a reviewer wants to see that
machinery, the README links to the decision-analytics-reconstruction repo instead.
This sentence may be copied into the README verbatim — it is a feature, not an omission.
