# ADR-015: Raw ENTSO-E writes — overlapping-request rows and per-row request_hash
Date: 2026-09-30  |  Status: accepted

## Context
ING-004 says raw parquet holds values "exactly as parsed", with "no dedup logic
beyond ING-003", and `request_hash` = sha256 of the request URL minus token.
ING-003 says a re-run "must not duplicate rows". The audit (2026-09-30, §2)
found two defects in `src/epra/ingest/entsoe.py`:

1. `ingest_dataset` ran `drop_duplicates()` over the concatenation of every
   response. That also collapsed identical rows *inside a single response*,
   which contradicts "raw means raw".
2. One `request_hash`, derived from the first chunk's window, was stamped on
   every month of a multi-year ingest, so the column did not describe the
   request that actually returned a row.

The rows the old dedup was there for do exist. `ingest_dataset` pages each
<=90-day chunk (ENTSO-E returns at most 100 documents per response), and
requests that start on a local-midnight boundary can also return the previous
delivery day's document. The same source fact then arrives in two responses.

## Decision
- Every parsed response frame is tagged with the `request_hash` of the query
  that produced it (`_fetch.query_request_hash`, the same token-free hash that
  keys the ING-009 cache). `_io.write_month(..., request_hash=None, ...)` keeps
  that per-row column. A month assembled from several requests records all of
  them.
- `entsoe._union_responses` drops a row only when an EARLIER response already
  returned a row with identical values. Duplicates within one response, and
  rows that differ in any value (restatements), are kept verbatim. Resolving
  those stays with dbt staging (DM-020). The number of refetched rows dropped
  is logged at INFO, so the step is never silent.

## Consequences
- The raw layer can now contain within-response duplicates that the old code
  hid. dbt's `predup_count_prices` test (DM-020) counts them, and the staging
  `qualify row_number()` resolves them.
- `request_hash` can differ between rows of one month file, so it is lineage,
  not a file-level key. No consumer relied on it being constant.

## Spec deviations
None. This ADR records how ING-003 and ING-004 are both satisfied when one
source fact is fetched by two overlapping requests.
