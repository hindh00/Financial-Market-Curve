{#
  dbt's default concatenates the base schema with +schema (e.g. "silver_gold")
  rather than using +schema as-is, which doesn't match this project's actual
  bronze/silver/gold schemas.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
