{#
    DM-060 composite-grain-key generic test. Hand-rolled with zero external
    dbt package dependency (ADR-001 lean-repo posture; a zero-package
    alternative to the commonly-used combination-of-columns uniqueness test),
    following dbt's own generic-test convention: a
    {% test <name>(model, column_name, ...) %} block returning rows that fail
    the test (here: any combination-of-columns value appearing more than
    once).

    Usage (dbt/models/staging/staging.yml — stg_gen_at_hourly's [ts_utc,
    psr_type] composite grain key):
        models:
          - name: stg_gen_at_hourly
            tests:
              - unique_combination_of_columns:
                  combination_of_columns: [ts_utc, psr_type]
#}
{% test unique_combination_of_columns(model, combination_of_columns) %}

with grouped as (
    select
        {{ combination_of_columns | join(', ') }},
        count(*) as n_rows
    from {{ model }}
    group by {{ combination_of_columns | join(', ') }}
)
select *
from grouped
where n_rows > 1

{% endtest %}
