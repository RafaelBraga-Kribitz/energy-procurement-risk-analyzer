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

**ÖSPI series pick: ADR-008 still formally `proposed`.** ADR-008 pins the AEA
continuously-published *strompreisindex* page as the sole 2019→latest
transcription source. The phase record (`.planning/phases/EPRA-03-m2-auxiliary-data/03-06-SUMMARY.md`)
states the maintainer confirmed that pick against the live publication on
2026-07-23 and the double-entry transcription has since been reconciled (§6),
but the ADR's own Status line has not been flipped by the human owner. ADRs are
append-only (GV-201): if the confirmation stands, the owner records it in a new
ADR that supersedes ADR-008.

**Base-only fallback (ING-104) — two sources of truth today.** `load_oespi`
derives `peak_available` from the data at load time
(`frame.attrs["peak_available"]`, `src/epra/ingest/oespi.py`) and would switch
to Base-only mode if any month lacked a Peak value. Independently,
`config/strategies.yaml` carries a static `peak_available: true` that
`epra.common.config.StrategyCfg` reads as a plain bool. No code reconciles the
two yet (the M6 simulator that would consume them is not built). They agree
for the committed series (every month 2019-01→2026-08 has a Peak value);
which signal the simulator honors if they ever disagree must be decided when M6
lands.

**Observed, unexplained: `oespi_peak < oespi_base` in every row.** All 92
committed months of `data/manual/oespi_monthly.csv` have a Peak index value
below the Base index value. Neither ADR-008 nor the transcribed source values
explain this; it is recorded here as an observed property, not interpreted.
Both columns are index points, not EUR/MWh (T-5) — do not read their ratio as
a peak/base price ratio; the EUR/MWh translation runs only through the ST-201…204
calibration anchors.

**ÖSPI's peak convention vs. this warehouse's internal peak definition
(ADR-011, finalized at M3).** `fct_price_monthly.price_peak_eur_mwh`
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
*(finalized at M6)* — the fixed-price service premium
(`fixed_premium_eur_mwh` in `config/strategies.yaml`; SPEC-05 §8 / SPEC-08 §6
default 5 EUR/MWh) is CALIBRATED, not observed; the 0 / 10 EUR/MWh
sensitivity results (ST-303) will be shown here.

## 4. The bootstrap cannot simulate an unprecedented regime
*(finalized at M6)* — Forward risk resamples history 2019→present; a regime
with no historical precedent is outside the model. The no-crisis conditional
variant (ST-401 step 4) partially addresses, does not solve, this.

## 5. Grid fees, taxes, and levies are excluded
Procurement-decision scope only (Charter §2): the analysis isolates the energy
price lever. Total electricity bill impact differs from the numbers shown here.

## 6. Data-quality caveats for 2025
*(M1/M2 findings recorded below; 2025 caveats cannot be assessed until the
re-backfill lands; finalized at M5)* — Any gate that required investigation
(R-8) is documented here with its resolution.

**Data horizon gap — no 2025 data ingested yet (open).** The committed
evidence shows the real ingested data stops well short of "latest complete
month":

- ENTSO-E: day-ahead prices end in 2024-02 — the 2024 row of ING-080 in
  `reports/ingestion/validation_2026-07-23.md` has 910 of 8,784 hourly prices
  (load 1,438) and is reported as a `boundary` year; `fct_generation_monthly`
  ends 2024-02 in `reports/warehouse/dbt_build_2026-07-24.md`. The gates pass
  only because ADR-006 scopes pass/fail to complete Vienna-local years
  (2019–2023). ING-083's negative-price check has therefore only been
  evaluated on 2023, and the 2024/2025 retrospective years configured in
  `config/strategies.yaml` have no price data.
- GeoSphere: the live pull covers 2019-01-01→2023-12-31 only (1826/1826 days,
  ING-094 section of the same validation report) although ING-093 specifies
  "2019-01-01 → latest". The truncation is not explained in the phase records.

Resolution requires a re-backfill to the latest complete month with the
maintainer's ENTSO-E token, re-running `make validate-ingest`, and recording
any 2025 gate investigation here. Until then no result may be stated for
2024–2025.

**M1 live-backfill findings (resolved 2026-07-22, `docs/BUILD_LOG.md`).** The
first real backfill exposed two silent data-loss bugs that offline fixtures had
masked: (1) ENTSO-E's 100-document response cap truncated each ≤90-day price
request to ~50 days (~44% of hours missing per year) — fixed by paging each
chunk; (2) chunk-boundary UTC-hour overlap let a later chunk overwrite an
earlier chunk's full month — fixed by accumulating all frames and writing each
UTC month once. A third, domain-alignment issue (gates bucketed by UTC year,
creating a phantom "2018") was resolved by ADR-006. After the fixes the
complete years 2019–2023 hold full hourly coverage.

**ÖSPI double-entry reconciliation (resolved 2026-07-23, Phase EPRA-03).**
Two independent human transcriptions were verified identical and reconciled
via `uv run python scripts/oespi_reconcile.py` (exit 0, 92 months
2019-01→2026-08) into the committed `data/manual/oespi_monthly.csv`;
`make validate-ingest` then showed a substantive real-data ING-103 PASS
(continuity/positivity/crisis-visibility/MoM). The two transcription entries
and the source publications used are held by the maintainer, not in this
repository; the committed CSV (constant `source_url`, ADR-008) is the source
of truth. The rows for 2026-07 and 2026-08 carry `retrieved_at=2026-07-23`,
i.e. they were transcribed before or during their delivery month. Secondary
sources describe the ÖSPI as computed from EEX futures for the coming quarters
and published for the *following* month, which would make that expected, but
the primary AEA page (`https://www.energyagency.at/fakten/strompreisindex`)
could not be fetched from the build environment on 2026-09-30, so the
publication lag is **not verified** (A-2). Until the maintainer confirms it, no
analysis may assume a particular lag when aligning ÖSPI months to spot months
(lookahead risk for ST-503 / ST-603).

## 7. No forecast-skill claim
This project makes no price forecasts (Charter O-1). Strategies are evaluated
against realized prices and bootstrap resampling of realized prices only.
