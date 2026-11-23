{#
  dbt's default behavior concatenates the profile's base schema with a
  model's +schema config (e.g. base "silver" + model +schema "gold" ->
  "silver_gold"), which doesn't match the bronze/silver/gold schemas that
  actually exist in Unity Catalog. Overriding this to just use the custom
  schema name as-is keeps models landing in "silver"/"gold" directly.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
