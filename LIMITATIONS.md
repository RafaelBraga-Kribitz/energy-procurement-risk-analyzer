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

**Open as of Phase EPRA-03 (M2) close-out, 2026-07-23: ÖSPI double-entry
reconciliation pending.** `data/manual/oespi_monthly.csv` (the reconciled
ÖSPI series ING-103 needs) does not exist yet. The two human transcriptions
required for double-entry (D-03) — `data/manual/oespi_monthly_entry1.csv`
and `oespi_monthly_entry2.csv` — are present locally but have not been
reconciled against each other. `make validate-ingest` currently SOFT-PASSES
ING-103 with the message "real ÖSPI data not yet transcribed ...
ING-101 double-entry human checkpoint pending (D-06), not a gate failure"
(see `reports/ingestion/validation_2026-07-23.md`). This is a
design-sanctioned deferral (D-06: real ÖSPI transcription is a human
checkpoint, never a CI blocker), not a gate failure — all 9 registered
gates (ING-080..085, ING-094, ING-103, ING-111) otherwise pass on real data
(GeoSphere station 30, live pull 2019-01→2023-12).

**To resolve:** reconcile the two entry files —
`uv run python scripts/oespi_reconcile.py` — until it exits 0 and writes
`data/manual/oespi_monthly.csv`; then delete
`data/manual/oespi_monthly_entry1.csv` and `oespi_monthly_entry2.csv`; then
re-run `make validate-ingest` and confirm ING-103 reports a real-data PASS
(not the informational soft-pass) before REQ-ING-01 is considered fully
closed.

## 7. No forecast-skill claim
This project makes no price forecasts (Charter O-1). Strategies are evaluated
against realized prices and bootstrap resampling of realized prices only.
