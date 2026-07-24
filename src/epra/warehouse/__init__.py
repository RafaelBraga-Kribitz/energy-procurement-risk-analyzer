"""Warehouse read layer (SPEC-02): D-02 build-report writer.

Reads the dbt-built warehouse read-only via `epra.common.db.connect`; renders
the human-readable ``reports/warehouse/dbt_build_<date>.md`` report. This
package never creates, builds, or mutates warehouse tables -- `dbt build`
(``make transform``) is the only writer.
"""
