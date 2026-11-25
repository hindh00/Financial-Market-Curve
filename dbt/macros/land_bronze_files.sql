{% macro land_bronze_files() %}
{#
  Bridges the raw JSON snapshots in the Volume into a queryable Delta table,
  since Volumes hold files, not tables. Run via `dbt run-operation
  land_bronze_files` before `dbt build` — see docs/architecture.md. Unions
  daily snapshots with backfill files (is_backfill=true, NULL pull_date since
  one backfill file spans years — stg_observations.sql derives it per-row).
#}
{% set sql %}
  CREATE OR REPLACE TABLE {{ var('catalog_name') }}.bronze.raw_observations AS
  SELECT
    get_json_object(value, '$.series_id') AS series_id,
    CAST(get_json_object(value, '$.pull_date') AS DATE) AS pull_date,
    get_json_object(value, '$.pull_timestamp_utc') AS pull_timestamp_utc,
    get_json_object(value, '$.source_url') AS source_url,
    CAST(get_json_object(value, '$.http_status') AS INT) AS http_status,
    get_json_object(value, '$.payload') AS payload_json,
    get_json_object(value, '$.observations_flat') AS observations_flat_json,
    CAST(get_json_object(value, '$.resolved_as_rrb_benchmark') AS BOOLEAN) AS resolved_as_rrb_benchmark,
    get_json_object(value, '$.rrb_resolution_timestamp_utc') AS rrb_resolution_timestamp_utc,
    get_json_object(value, '$.rrb_description') AS rrb_description,
    false AS is_backfill,
    _metadata.file_path AS source_file_path,
    _metadata.file_modification_time AS file_modified_at
  FROM read_files(
    '/Volumes/{{ var('catalog_name') }}/bronze/raw_valet',
    format => 'text',
    wholeText => true
  )
  WHERE _metadata.file_path NOT LIKE '%/_dq_results/%'
    AND _metadata.file_path NOT LIKE '%/_backfill/%'

  UNION ALL

  SELECT
    get_json_object(value, '$.series_id') AS series_id,
    CAST(NULL AS DATE) AS pull_date,
    get_json_object(value, '$.pull_timestamp_utc') AS pull_timestamp_utc,
    get_json_object(value, '$.source_url') AS source_url,
    CAST(get_json_object(value, '$.http_status') AS INT) AS http_status,
    get_json_object(value, '$.payload') AS payload_json,
    get_json_object(value, '$.observations_flat') AS observations_flat_json,
    CAST(get_json_object(value, '$.resolved_as_rrb_benchmark') AS BOOLEAN) AS resolved_as_rrb_benchmark,
    get_json_object(value, '$.rrb_resolution_timestamp_utc') AS rrb_resolution_timestamp_utc,
    get_json_object(value, '$.rrb_description') AS rrb_description,
    true AS is_backfill,
    _metadata.file_path AS source_file_path,
    _metadata.file_modification_time AS file_modified_at
  FROM read_files(
    '/Volumes/{{ var('catalog_name') }}/bronze/raw_valet/_backfill',
    format => 'text',
    wholeText => true
  )
{% endset %}

{% do run_query(sql) %}
{% do log("Landed bronze files into " ~ var('catalog_name') ~ ".bronze.raw_observations", info=True) %}
{% endmacro %}


{% macro land_dq_results_files() %}
{#
  Bridges the Python-side DQ check results (ingestion/land_dq_results.py)
  into a queryable table — separate from land_bronze_files() since the
  envelope shape differs (a `results` array, not observations).
#}
{% set sql %}
  CREATE OR REPLACE TABLE {{ var('catalog_name') }}.bronze.raw_dq_results AS
  SELECT
    CAST(get_json_object(value, '$.pull_date') AS DATE) AS landed_pull_date,
    get_json_object(value, '$.pull_timestamp_utc') AS pull_timestamp_utc,
    explode(
      from_json(
        get_json_object(value, '$.results'),
        'array<struct<check_name:string,series_id:string,observation_date:string,pull_date:string,status:string,severity:string,details:string>>'
      )
    ) AS check_result
  FROM read_files(
    '/Volumes/{{ var('catalog_name') }}/bronze/raw_valet/_dq_results',
    format => 'text',
    wholeText => true
  )
{% endset %}

{% do run_query(sql) %}
{% do log("Landed DQ result files into " ~ var('catalog_name') ~ ".bronze.raw_dq_results", info=True) %}
{% endmacro %}
