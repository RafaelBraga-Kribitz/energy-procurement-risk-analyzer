# ADR-018: Structured synthetic fixture market over the full analysis window
Date: 2026-10-14  |  Status: accepted

Builds on ADR-016 (fixture bootstrap contracts); does not supersede it.
Related: Charter P-1 / A-2, SPEC-04 AN-304, SPEC-05 ST-602, AGENTS.md M5/M6.

## Context

M5 and M6 have gates that only mean something on data with market structure:
AN-304 needs a calm 2019 and a high-volatility 2021-09..2023-06; ST-602 needs a
2022 spot level above pre-crisis lock prices; ST-201 needs the 2019 reference
year; the retrospective needs 2021-2025. The ADR-016 fixture was white noise
over 2022-2024 only, so none of these code paths could run in CI or in a
container without an ENTSO-E token (the case for this build session: no
token, and ENTSO-E/GeoSphere hosts are not reachable).

## Decision

1. The CI fixture default window becomes 2019-01-01 → 2026-09-30 (fixed, for
   determinism), with the calendar spine running 18 months further (SG-15).
2. Synthetic AT spot = monthly level × daily AR(1) multiplicative shock ×
   hour shape − a midday solar dip growing per year + hourly noise. The
   monthly level is the committed ÖSPI base series led by 4 months × 0.42
   EUR/MWh per index point; volatility jumps when the level exceeds 120.
   DE-LU = AT minus a small positive spread. From 2025-10 the fixture emits
   PT15M rows (R-2 resolution mix). System load carries a heating-degree
   effect; temperature is a seasonal sinusoid plus noise. All seeded.
3. `data/manual/oespi_monthly.csv` is READ (never written) for that level path.
4. The bootstrap writes `data/raw/_SYNTHETIC_FIXTURE.txt`. Every analytics,
   strategy and SSOT artifact built while the marker exists carries the
   FIXTURE banner (markdown) or watermark (PNG) from
   `epra.common.provenance`.

## Consequences

- `make all` runs end to end, network-free, with every gate exercised.
- Fixture numbers are pipeline evidence only. They are never results, never
  quoted in README/EXEC_SUMMARY as findings, and are replaced by the first
  real `make backfill` run (the bootstrap refuses to overwrite real data, and
  real ingestion never writes the marker).
- Gates passing on fixtures prove the code path, not the market finding; the
  real-data run must pass them again (recorded in BUILD_LOG).

## Spec deviations (list REQ IDs affected, or "none")

None. P-1 (no synthetic prices) governs published results; ADR-016 already
scopes synthetic fixture data to CI/test use, and the provenance banner keeps
that boundary enforceable.
