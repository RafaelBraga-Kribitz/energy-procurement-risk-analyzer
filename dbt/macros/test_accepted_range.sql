{#
    DM-061 accepted-range generic test. Hand-rolled with zero external dbt
    package dependency (ADR-001 lean-repo posture) following dbt's own
    generic-test convention: a
    {% test <name>(model, column_name, ...) %} block returning rows that
    fail the test (rows outside [min_value, max_value]).

    Usage (dbt/models/marts/marts.yml or staging.yml):
        columns:
          - name: price_at_eur_mwh
            tests:
              - accepted_range: {min_value: -500, max_value: 5000}
#}
{% test accepted_range(model, column_name, min_value=none, max_value=none) %}

select *
from {{ model }}
where
    {% if min_value is not none %} {{ column_name }} < {{ min_value }} {% endif %}
    {% if min_value is not none and max_value is not none %} or {% endif %}
    {% if max_value is not none %} {{ column_name }} > {{ max_value }} {% endif %}

{% endtest %}
