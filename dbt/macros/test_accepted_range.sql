{#
    DM-061 accepted-range generic test. Hand-rolled with zero external dbt
    package dependency (ADR-001 lean-repo posture) following dbt's own
    generic-test convention: a
    {% test <name>(model, column_name, ...) %} block returning rows that
    fail the test (non-NULL values outside the accepted range).

    Arguments:
      min_value / max_value -- bounds; at least one is REQUIRED (a test with
        neither would render an empty predicate and silently pass, so it is
        a compile-time error instead).
      inclusive (default true) -- false makes both bounds strict, e.g.
        DM-061 `oespi_base > 0` is {min_value: 0, inclusive: false}.

    Usage (dbt/models/marts/facts_price.yml; dbt >= 1.10 syntax, ADR-012):
        columns:
          - name: price_at_eur_mwh
            data_tests:
              - accepted_range:
                  arguments: {min_value: -500, max_value: 5000}
#}
{% test accepted_range(model, column_name, min_value=none, max_value=none, inclusive=true) %}

{%- if min_value is none and max_value is none -%}
    {{ exceptions.raise_compiler_error(
        "accepted_range on " ~ model ~ "." ~ column_name
        ~ ": at least one of min_value / max_value is required"
    ) }}
{%- endif -%}
{%- set below = "<" if inclusive else "<=" -%}
{%- set above = ">" if inclusive else ">=" -%}

select *
from {{ model }}
where
    {% if min_value is not none %} {{ column_name }} {{ below }} {{ min_value }} {% endif %}
    {% if min_value is not none and max_value is not none %} or {% endif %}
    {% if max_value is not none %} {{ column_name }} {{ above }} {{ max_value }} {% endif %}

{% endtest %}
