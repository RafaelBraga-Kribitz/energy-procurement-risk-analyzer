{#
    Override dbt's built-in generate_schema_name macro (DM-003, SG-13, ADR-009).

    Default dbt behavior concatenates `<target.schema>_<custom_schema_name>` (e.g.
    `main_staging`) to avoid schema collisions across developers/CI runs sharing one
    warehouse. This project deliberately OMITS that default-schema prefix so that
    `+schema: staging` / `+schema: marts` (dbt/dbt_project.yml) and the
    `dim_strategy` seed's `+schema: marts` config land in DuckDB schemas literally
    named `staging` / `marts`, not `main_staging` / `main_marts`.

    dbt's own docs label this pattern unsafe for shared dev/CI databases (a second
    developer or a second CI run targeting the same warehouse file could silently
    overwrite the first's schemas). It is accepted here because dbt/profiles.yml
    defines exactly one local `dev` target against one local DuckDB file — a single-
    operator warehouse, never a shared/concurrent one (see ADR-009 for the full
    tradeoff record; do not generalize this macro to any future multi-target or
    multi-developer dbt project without revisiting that decision).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
