# LIMITATIONS

Honesty artifacts are load-bearing here (A-8): this file is an acceptance
criterion (DL-9), not decoration. Sections follow SPEC-08 §6; each is completed
in the milestone that produces the relevant numbers. Placeholder sections state
what WILL be written so no limitation can be quietly dropped.

## 1. The consumer load profile is constructed, not measured
*(finalized at M4)* — Reference load profile is constructed (CALIBRATED), not
measured; construction rules in SPEC-03. Real industrial RLM load data would
change levels but not the ordinal ranking logic of strategies; the
`flat_baseload` sensitivity (LP-030) bounds the shape effect. The computed
sensitivity numbers land here at M6.

## 2. ÖSPI as forward/contract price proxy
*(finalized at M6)* — What the index captures, what it misses (individual
supplier margins, credit terms, volume flexibility clauses). Direction of the
likely bias unknown — this will be said plainly (R-5). Calibration anchors
(p_ref_base, p_ref_peak, oespi_base_ref, oespi_peak_ref) quoted here per ST-204.

**ÖSPI series pick is provisional.** ADR-008 pins the AEA continuously-published
*strompreisindex* page as the sole 2019→latest transcription source, but that
pick is explicitly flagged pending human confirmation at T2.05 transcription
time (D-01/D-04) — it is a strong research-backed candidate, not a locked
fact, until the human double-entry transcription (ING-101) actually happens.
If monthly Peak values turn out to be unavailable/discontinuous for part of
the 2019→latest window, the pipeline falls back to Base-only mode (ING-104,
`load_oespi`'s `peak_available=False` signal) rather than failing outright —
see ADR-008 for the mechanism and the crisis-visibility gate (ING-103) that
still holds in that mode.

**ÖSPI's peak convention vs. this warehouse's internal peak definition
(SG-14 / ADR-011, finalized at M3).** `fct_price_monthly.price_peak_eur_mwh`
is computed from the ONE holiday-aware `is_peak_hour` flag (Mon-Fri, 08-20
local, excluding Austrian public holidays — sourced from `dim_calendar`/
ING-110) applied everywhere in this warehouse. `oespi_peak`, left-joined from
the externally-transcribed ÖSPI index, is produced by AEA's own methodology
and may classify holiday weekday hours differently (e.g. as peak regardless
of the public-holiday calendar). This is a genuine discrepancy between an
internally-computed column and an external reference series that this
project does not resolve by recomputing either side — see ADR-011. Any
calibration anchor derived from the `price_peak_eur_mwh`/`oespi_peak` ratio
absorbs this level offset by construction, since the ratio is calibrated
against the actual co-observed pair rather than an assumed-identical peak
definition.

## 3. The fixed-price premium is an assumption
*(finalized at M6)* — 5 EUR/MWh service premium is CALIBRATED, not observed;
the 0 / 10 EUR/MWh sensitivity results (ST-303a) will be shown here.

## 4. The bootstrap cannot simulate an unprecedented regime
*(finalized at M6)* — Forward risk resamples history 2019→present; a regime
with no historical precedent is outside the model. The no-crisis conditional
variant (ST-401 step 4) partially addresses, does not solve, this.

## 5. Grid fees, taxes, and levies are excluded
Procurement-decision scope only (Charter §2): the analysis isolates the energy
price lever. Total electricity bill impact differs from the numbers shown here.

## 6. Data-quality caveats for 2025
*(finalized at M1/M5)* — Any gate that required investigation (R-8) is
documented here with its resolution.

**RESOLVED 2026-07-23 (Phase EPRA-03 close-out): ÖSPI double-entry
reconciliation complete.** The human double-entry transcription was completed
(`data/manual/oespi_monthly_entry1.csv` == `oespi_monthly_entry2.csv`, verified
identical) and reconciled via `uv run python scripts/oespi_reconcile.py`
(exit 0, 92 months 2019-01→2026-08) into `data/manual/oespi_monthly.csv`.
`make validate-ingest` now exits 0 with **ING-103 a substantive real-data PASS**
(continuity/positivity/crisis-visibility/MoM checks all pass) — no longer the
informational soft-pass. All 9 registered gates (ING-080..085, ING-094,
ING-103, ING-111) pass on real data (GeoSphere station 30, live pull
2019-01→2023-12; ÖSPI 2019-01→2026-08). REQ-ING-01 fully closed.

*Housekeeping (ING-101 step 4):* the transient double-entry working files
`data/manual/oespi_monthly_entry1.csv`, `oespi_monthly_entry2.csv`, and
`oespi_monthly_entry.csv` remain on disk (untracked) — safe to delete now that
`oespi_monthly.csv` is the committed source of truth.

## 7. No forecast-skill claim
This project makes no price forecasts (Charter O-1). Strategies are evaluated
against realized prices and bootstrap resampling of realized prices only.
