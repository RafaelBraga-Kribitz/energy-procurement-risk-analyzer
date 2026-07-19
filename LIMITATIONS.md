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

## 7. No forecast-skill claim
This project makes no price forecasts (Charter O-1). Strategies are evaluated
against realized prices and bootstrap resampling of realized prices only.
