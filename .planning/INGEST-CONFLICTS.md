## Conflict Detection Report

### BLOCKERS (0)

(none)

### WARNINGS (11)

[WARNING] SG-01 proposed EntsoeRawClient vs SPEC ING-022 EntsoePandasClient
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-01 proposes `EntsoeRawClient` as transport with own Appendix-A parser; PandasClient never used for persistence
  Impact: Non-binding gap proposal conflicts with explicit SPEC-01 ING-022 client choice; synthesized intel retains SPEC authority until ADR adoption
  → Adopt via T1.02 ADR if EntsoeRawClient approach is chosen; until then implement per ING-022 or document ADR deviation

[WARNING] SG-02 proposed zone rule for ING-042 latest complete month
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-02 proposes min(AT prices, DE-LU prices) for `latest_complete_month()`
  Impact: SPEC-01 ING-042 defines "price data" without zone enumeration; proposal is non-binding interpretation
  → Adopt via T1.08 ADR before implementing zone-specific logic, or implement strict ING-042 text and escalate ambiguity

[WARNING] SG-03 proposed reference-year 2019 for consumer_peak_share
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-03 proposes per-year computation with 2019 reference value published to SSOT
  Impact: SPEC-03 LP-020 requires exact peak share to SSOT without specifying reference-year rule; proposal adds interpretation
  → Adopt via T4.03 ADR before publishing reference-year convention

[WARNING] SG-05 proposed fct_price_hourly column enumeration
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-05 proposes frozen column list (ING-110 attrs + season, hdd_18, cdd_22)
  Impact: SPEC-02 §5 says "+ all dim_calendar attributes" without frozen enumeration; contract YAML adoption pending
  → Complete T3.04 contract YAML review/adoption before treating enumeration as binding

[WARNING] SG-06 proposed fixture bootstrap for M3 marts
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-06 proposes stand-in parquet for `fct_consumer_load_hourly` / `fct_procurement_cost_monthly` until M4/M6
  Impact: SPEC-02 §5 defines mart contracts but does not specify fixture stand-ins; proposal is non-binding build-order workaround
  → Adopt via T3.06 ADR before committing fixture bootstrap pattern

[WARNING] SG-07 proposed ST-401 day-mapping algorithm
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-07 pins day-index/weekend-type/DST rules beyond SPEC-05 ST-401 step 3 text
  Impact: SPEC ST-401 gives high-level alignment rule; gap proposal adds deterministic algorithm not yet in SPEC
  → Adopt via T6.07 ADR before implementing pinned algorithm

[WARNING] SG-08 proposed P95/CVaR numerical methods
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-08 proposes `numpy.quantile(method="linear")` and CVaR95 = mean of ceil(0.05·N) highest costs
  Impact: SPEC-05 ST-403 specifies CVaR95 as mean of worst 5% but not quantile interpolation method
  → Adopt via T6.07 ADR before pinning numerical methods in `summarize()`

[WARNING] SG-09 proposed GV-303 rounding and updated_at rules
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-09 proposes round_half_up match rule and mtime-based `updated_at`
  Impact: SPEC-08 GV-303 references "rounding documented in the script" without defining rule; proposal non-binding
  → Adopt via T6.08/09 ADR before implementing checker rounding semantics

[WARNING] SG-13 proposed dbt generate_schema_name override
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-13 proposes macro returning custom schema literally (avoid `main_staging`)
  Impact: SPEC-02 DM-003 names schemas `staging`/`marts` but does not specify dbt macro override; proposal non-binding
  → Adopt via T3.01 ADR before committing macro

[WARNING] SG-15 proposed dynamic calendar end and rebuild order
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-15 proposes `--end` pre-M1, post-M1 regeneration to latest_complete_month + horizon + margin, profile rebuilt after calendar
  Impact: SPEC-01 ING-110 and SPEC-03 LP-003 define forward window but not pre-M1 bootstrap mechanics
  → Adopt via T2.01 ADR before implementing dynamic calendar rebuild protocol

[WARNING] SG-18 proposed refresh.yml empty-diff skip
  Found: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md SG-18 proposes skip PR creation when zero report changes
  Impact: SPEC-07 refresh.yml behavior for no-op months not specified; proposal is non-binding implementation detail
  → Confirm at T7.05 implementation or document in ADR if behavior affects CI contract

### INFO (6)

[INFO] Auto-resolved: ADR-002 > SPEC-07 §3 on dev typing stubs
  Note: docs/ADR/ADR-002_typing-stub-dev-dependencies.md (locked) adds dev-only pandas-stubs, types-PyYAML, types-requests and statsmodels ignore override; SPEC-07 §3 dependency list silent on stubs — ADR wins, output contract preserved (strict first-party checking)

[INFO] Auto-resolved: ADR-001 > any external governance kit proposal
  Note: docs/ADR/ADR-001_light-governance-no-external-kit.md (locked) prohibits vendoring governance-bootstrap kit; aligns with SPEC-08 §7 and Charter §4.2 O-5

[INFO] Intra-suite SPEC cross-ref cycles (non-blocking)
  Note: Cross-ref graph among SPEC-01..08 contains cycles (e.g. SPEC-02 ↔ SPEC-03 ↔ SPEC-05); expected modular documentation references within single authoritative spec suite subordinate to Charter — synthesis proceeds on all SPECs

[INFO] SG-14 peak definition aligns with ING-110 and LP-020 over Charter glossary shorthand
  Note: Charter glossary peak omits holidays; SPEC-01 ING-110 and SPEC-03 LP-020 define holiday-aware peak — synthesized intel uses ING-110/LP-020; SG-14 proposal consistent but pending T3.04 ADR for LIMITATIONS note

[INFO] SG-16 and SG-17 marked resolved in gaps tracker
  Note: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md records SG-16 (staging dedup defense-in-depth) and SG-17 (consumption kind persisted, filtered in staging) as spec-consistent — no conflict with SPECs

[INFO] SG-10 and SG-11 consistent with SPEC requirements
  Note: SG-10 (`subdiv='6'`) matches ING-110; SG-11 (binding ING-082 gate, ADR on failure) matches SPEC-01 validation philosophy — proposals reinforce existing SPEC text
