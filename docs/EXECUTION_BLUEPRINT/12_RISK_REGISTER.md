# 12 — RISK REGISTER (execution-level; extends Charter §8 R-1..R-8)

Charter risks R-1..R-8 remain authoritative; rows below either operationalize
them (detection/fallback detail) or add blueprint-identified risks (RB-9+).
Review this file at each phase start (checklist trigger in [01_PHASES.md](01_PHASES.md)).

| ID | Risk (phase) | L×I | Detection | Mitigation | Fallback |
|----|--------------|-----|-----------|------------|----------|
| R-1 | Token approval delay (M1) | M×H | calendar: > 5 business days | Phase W plan absorbs ~3 days idle-free ([04_DEPENDENCIES.md](04_DEPENDENCIES.md) §4.6) | continue M2+M3-on-fixtures; escalate to ENTSO-E helpdesk; critical path pauses only at T1.10 |
| R-2 | 15-min MTU mixed resolutions (M1/M3) | H×H | ING-060 inference test; ING-082 gate | resolution-aware parsing; canonical hourly in staging; PT15M + mixed-month fixtures | per-day resolution partitioning; ADR + parser adaptation preserving §7 contracts |
| R-3 | A03 omitted points (M1) | M×M | fill counts in report; ING-080 coverage | ING-063 rule + independent hour-coverage gate | if fills > expected scale, raw REST comparison for one sample month |
| R-4 | ÖSPI transcription errors (M2) | M×H | reconcile diff; ING-103 MoM gate | double-entry protocol (implemented) | third reading of disputed months; document in ADR-004 |
| R-5 | ÖSPI-as-forward proxy validity (M6) | certain×M | n/a (modeling choice) | ST-502 captions; LIMITATIONS §2; premium sensitivity | none needed — this is a documented assumption, not a defect |
| R-6 | Scope creep (all) | H×H | PR review vs Charter §4.2; AP-12 | WBS is closed — new work requires a WBS change + traceability row first | revert; move idea to README "Future work" line |
| R-7 | GeoSphere naming drift (M2) | L×L | discovery procedure fails loudly | ING-091 discovery + ADR | alternate Graz station (2nd longest record), ADR'd |
| R-8 | 2025 data anomalies (M1/M5) | M×M | ING-082/-083 gates; AN-304 | investigation protocols (guide §5.1) | documented exclusion of affected period + LIMITATIONS §6 |
| RB-9 | entsoe-py RawClient behavior differs from assumption SG-01 (M1) | M×M | T1.02 spike fails against live API on day 1 of token | parser owns contracts; entsoe-py is transport only | Appendix A raw REST via `requests` (sanctioned fallback, ADR) — `_fetch` interface unchanged |
| RB-10 | dbt-duckdb schema-name prefixing breaks contract test (M3) | H×L | first `dbt build` schema query | SG-13 macro from day one (T3.01) | pin adapter version; adjust macro; never adjust the contract to reality |
| RB-11 | HMM nondeterminism across platforms/BLAS (M5) | M×M | AN-705 ×2 on CI vs local produce different SSOT values | seeded restarts; deterministic tie-break; float64 | pin state assignment by sorted std + document; if still unstable, run A3 fit only via `make analyze` on one canonical platform and commit the regime parquet (ADR) |
| RB-12 | Coverage gate friction as stub tests are deleted (M4–M6) | M×L | coverage dips at PR time | implement + test in same commit (W-1); stubs deleted only when replaced by real tests | temporary per-module coverage annotation NEVER — split the PR's test debt instead |
| RB-13 | Golden laundering / silent regeneration (M6+) | L×H | golden file in diff without rationale (AP-20) | dirty-tree refusal in generator; human approval step | revert; re-run EN-072 flow properly |
| RB-14 | Windows/CI path + line-ending divergence (all) | M×L | CI green but local fail or vice versa | pathlib everywhere; UTF-8 explicit; CI is the arbiter | add `.gitattributes` normalizing to LF (do at first symptom, chore commit) |
| RB-15 | SDAC 15-min data volume inflates backfill time/memory (M1) | M×L | backfill exceeds §7.2 budget | monthly-file partitioning; per-chunk frames | process per-month instead of per-quarter frames; budgets re-measured, ADR if raised |
| RB-16 | ÖSPI publication lag breaks monthly refresh (ops) | H×L | EN-083 coverage check | suppression rule (not extrapolation) + PR-body notice | strategy outputs resume automatically when human commits the month |
| RB-17 | Agent context loss / blueprint drift across sessions (all) | M×H | PR deviates from WBS/module contracts without ADR/SG note | session protocol §0.8 (read-before-code); traceability check per PR | reviewer rejects; blueprint updated in same PR when reality legitimately diverged |
| RB-18 | Scientific credibility risk: a reviewer disputes calibration choices (portfolio) | M×M | external feedback | anchors + premium + proxy all CALIBRATED-tagged, sensitivity-bounded, LIMITATIONS-documented | the answer is the sensitivity table — by design there is no undocumented assumption to defend |

**Portfolio-level risk statement:** the single biggest project risk is not
technical — it is shipping M1–M5 and stalling before M6/M7 where the audience
value (euro answer, dashboard, exec summary) materializes. Mitigation: the
critical path in [04_DEPENDENCIES.md](04_DEPENDENCIES.md) §4.4 front-loads
nothing optional; sensitivities and no-crisis variants are scoped small (ST-303
exactly three; O-5/O-7 guards) so M6 cannot balloon.
