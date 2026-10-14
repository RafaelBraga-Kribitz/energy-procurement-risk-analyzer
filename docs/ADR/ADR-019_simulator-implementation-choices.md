# ADR-019: Strategy simulator — choices the spec leaves open
Date: 2026-10-14  |  Status: accepted

Related: SPEC-05 §§2-6, SPEC-02 §5, LIMITATIONS §2/§4, ADR-018.

## Context

Building M6 surfaced five points where SPEC-05 is silent or where its literal
wording cannot be executed. Each is decided once here so the code, the tests
and LIMITATIONS agree.

## Decision

1. **ÖSPI source = `marts.fct_price_monthly`.** The staging view
   `stg_oespi_monthly` resolves its CSV relative to `dbt/` and cannot be read
   from Python. The monthly price mart already carries `oespi_base/peak` per
   priced month, which also gives ONE data horizon: an index month is
   "observed" (ST-402) only when its spot month is in the warehouse.
2. **S3 lock-window gap in the forward run (ST-402).** A lock month can be
   neither observed nor a simulated target month (e.g. latest data month
   2026-09, ÖSPI only to 2026-08, delivery year 2027 locks on 2026-07..12).
   Such a month uses the last observed ÖSPI value carried forward. No
   synthetic index value is invented; the choice is tested.
3. **No-crisis pool (ST-401.4).** A year's "December regime" is the modal
   AN-302 label of its December days; years labelled `crisis` are excluded.
   A year with no December in the data (the partial current year) is kept,
   since nothing marks it as crisis.
4. **Sensitivity (b) flat_baseload (ST-303)** prices the flat profile with its
   OWN anchors (ST-201/202 are consumer-specific) and its own peak share
   (`consumer_peak_share_flat_baseload`, written by `make profile`). The
   sensitivity grid values live in `config/strategies.yaml` (`sensitivity:`),
   not in code (ST-003).
5. **Build order.** `make transform` builds every model except
   `fct_procurement_cost_monthly+`; `make simulate` builds that mart after the
   simulator writes its parquet. A fresh clone therefore never needs a
   stand-in cost file (ADR-016 stand-ins remain for the CI `dbt build` job).
   `peak_available` (ING-104): the config flag selects the formula; if it says
   `true` and a needed peak index value is missing, the engine raises instead
   of silently switching to base-only.

## Consequences

- Forward results for delivery years whose lock window straddles the data
  edge rest partly on a carried-forward index value; LIMITATIONS §4 says so.
- The simulator never reads a file the warehouse does not expose.

## Spec deviations (list REQ IDs affected, or "none")

ST-402 (gap rule added), ST-401 step 4 (December-regime definition made
explicit). Output contracts unchanged.
