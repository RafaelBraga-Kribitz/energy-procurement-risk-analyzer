{#
    DM-050 no-gap month-spine helper. Hand-rolled with zero external dbt
    package dependency (ADR-001 lean-repo posture) using DuckDB's native
    generate_series over
    date_trunc('month', ...) — emits one row per local calendar month
    between the two bounds (inclusive), for anti-joining against a mart's
    distinct months to detect gaps.

    Usage (see dbt/tests/no_gap_*.sql):
        with spine as (
            {{ month_spine("(select min(month_local) from actual)",
                            "(select max(month_local) from actual)") }}
        )
        select * from spine left join actual using (month_local)
        where actual.month_local is null
#}
{% macro month_spine(min_month_expr, max_month_expr) %}
    select unnest(
        generate_series(
            date_trunc('month', {{ min_month_expr }}),
            date_trunc('month', {{ max_month_expr }}),
            interval '1 month'
        )
    )::date as month_local
{% endmacro %}
