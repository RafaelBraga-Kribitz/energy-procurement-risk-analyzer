# dbt project — built at M3

Skeleton only for now: project config, committed DuckDB profile (relative path,
no credentials), and the `dim_strategy` seed (SPEC-02 §4, verbatim).

M3 builds, per SPEC-02:

- `models/sources.yml` — raw parquet exposed via `read_parquet` (DM-004); no
  other model touches files directly.
- `models/staging/` — the eight staging views of §3, exact contracts (incl. the
  15-min → hourly MEAN aggregation, trap T-2, and the single sanctioned dedup
  rule DM-020).
- `models/marts/` — the six marts of §5; the M3 exit gate diff-checks their
  schemas against a committed contract YAML.
- `tests/` — DM-060..066 (grain uniqueness, accepted ranges, row counts, the
  2022-08 reconciliation singular test, DST 23/25 hour tests, freshness).
- A fixture-bootstrap script so CI's dbt job runs on `tests/fixtures/` parquet
  without network (EN-080 job 3).

Timezone doctrine (DM-010..012): `ts_utc` is the join key everywhere; local
attributes come ONLY from `dim_calendar`; no model calls timezone conversion
functions independently.
