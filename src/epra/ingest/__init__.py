"""Ingestion layer (SPEC-01): external sources → data/raw/ parquet.

One module per source (ING-001): entsoe, geosphere, oespi, calendar; validate
runs the §8-§11 gates. Raw means raw (ING-004): no unit conversion, no gap
filling here — that is dbt staging's job (SPEC-02).
"""
