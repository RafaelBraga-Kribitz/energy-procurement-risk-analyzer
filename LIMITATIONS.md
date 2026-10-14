# LIMITATIONS

Honesty artifacts are load-bearing here (A-8): this file is an acceptance
criterion (DL-9), not decoration. Sections follow SPEC-08 §6. Numbers are never
retyped here: each section names the `reports/NUMERIC_SSOT.md` keys that hold them.

## 1. The consumer load profile is constructed, not measured
Reference load profile is constructed (CALIBRATED), not measured; construction
rules in SPEC-03 (built by `make profile`, M4). Real industrial RLM load data would
change levels but not the ordinal ranking logic of strategies; the
`flat_baseload` sensitivity (LP-030) bounds the shape effect: its five-year
cost per strategy and wrong-strategy total are the `flat_baseload` row of
`reports/strategies/sensitivity_matrix.md` and the `sens_flat_baseload_*` keys
of `reports/NUMERIC_SSOT.md` (numbers are quoted only from there, A-6).

## 2. ÖSPI as forward/contract price proxy
The ÖSPI is built by the Austrian Energy Agency from futures-based fictitious
procurement, so it captures the forward market's price LEVEL and its lag
behind spot. It misses everything that makes a real supplier offer differ from
the market: individual supplier margins, credit and payment terms, volume
tolerance and flexibility clauses, and the date on which a buyer actually
signs. The direction of the resulting bias is unknown, and this project does
not claim one (R-5). S2/S3/S4 prices are translated from index points to
EUR/MWh only through the four CALIBRATED anchors `p_ref_base`, `p_ref_peak`,
`oespi_base_ref`, `oespi_peak_ref` (ST-201…204), whose values are the keys of
the same names in `reports/NUMERIC_SSOT.md`. Every strategy output carries the
caption "Contract prices proxied via ÖSPI (futures-based index); premiums are
calibrated assumptions — see LIMITATIONS." (ST-502).

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
for the committed series (every month 2019-01→2026-08 has a Peak value).
Resolved at M6 (ADR-019): the config flag selects the formula, and if it says
`true` while a needed Peak value is missing, the simulator stops with an error
instead of silently switching to Base-only.

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
The fixed-price service premium (`fixed_premium_eur_mwh` in
`config/strategies.yaml`, default 5 EUR/MWh per SPEC-05 §8) is CALIBRATED, not
observed: no supplier's actual risk margin was available. The 0 and 10 EUR/MWh
reruns (ST-303) are the `premium_0` / `premium_10` rows of
`reports/strategies/sensitivity_matrix.md` (SSOT keys `sens_premium_0_*`,
`sens_premium_10_*`). Where they change the best strategy, the base-case
ranking between fixed and spot is within the premium's uncertainty and is
reported as such.

## 4. The bootstrap cannot simulate an unprecedented regime
Forward risk resamples whole historical months 2019→present (seeded block
bootstrap, 2,000 paths). A regime with no historical precedent — a sharper
crisis than 2022, a structural break in market design — is outside the model,
and P95/CVaR95 understate such a tail. The no-crisis conditional variant
(ST-401 step 4, pool limited to years whose December regime is not `crisis`)
shows how much of the tail comes from the 2022 months; it partially addresses,
does not solve, this. Two further simplifications (ADR-019): a fixed-price lock
month that is neither observed nor simulated uses the last observed ÖSPI value
carried forward, and hybrid strategies split each hour's volume uniformly
between the fixed and spot legs (ST-107).

## 5. Grid fees, taxes, and levies are excluded
Procurement-decision scope only (Charter §2): the analysis isolates the energy
price lever. Total electricity bill impact differs from the numbers shown here.

## 6. Data-quality caveats for 2025
*(M1/M2 findings recorded below; 2025 caveats cannot be assessed until the
re-backfill lands; finalized at M5)* — Any gate that required investigation
(R-8) is documented here with its resolution.

**All committed results are fixture-based until the real-data run (open,
2026-10-14).** M4–M7 were built in an environment without the ENTSO-E token
and without network access to ENTSO-E or GeoSphere. Every committed analytics,
strategy, SSOT, data-quality and executive-chart artifact therefore comes from
the seeded synthetic CI fixture (ADR-018) and carries a FIXTURE banner or
watermark; the README shows no numbers in that state. The gates (AN-304,
ST-602, GV-303) passing on the fixture prove the code paths, not the market
findings. Resolution: `make backfill && make geosphere && make calendar &&
make validate-ingest && make all` with the token; any gate that then needs
investigation is recorded here (R-8).

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
  "2019-01-01 → latest". No code path truncates the pull (checked
  2026-09-30). The phase records show the run was invoked with an explicit
  `--end` (`03-06-PLAN.md`, `03-06-SUMMARY.md`), presumably matching the
  ENTSO-E horizon of the time. The old ING-094 gate measured coverage against
  the data's own first and last day, so it could not see the truncation. It
  now measures against the ING-093 window and will FAIL until GeoSphere is
  re-pulled.

Likely cause of the ENTSO-E horizon (found 2026-09-30): `make backfill`
without `--end` defaulted its end date to the latest complete month *already
on disk*, so every re-run stopped where the previous one had. It now defaults
to the last complete calendar month (ING-040). Resolution: with the
maintainer's ENTSO-E token, run `make backfill`, `make geosphere` (no
`--end`) and `make calendar` (the spine now uses local-day bounds, ADR-017),
then `make validate-ingest` and `make warehouse`, and record any 2024/2025
gate investigation here. Until then no result may be stated for 2024–2025.

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
