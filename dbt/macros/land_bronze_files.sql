{% macro land_bronze_files() %}
{#
  Bridges the raw JSON snapshots in the Unity Catalog Volume
  (/Volumes/fmc/bronze/raw_valet) into a queryable Delta table
  (fmc.bronze.raw_observations), since Volumes hold files, not tables.

  Run via `dbt run-operation land_bronze_files` as the first task in the
  daily Databricks Job, before `dbt build` — see docs/architecture.md for
  the full job task chain. A full-refresh CREATE OR REPLACE is used rather
  than incremental COPY INTO/Auto Loader: data volumes here are small
  (a handful of series, one snapshot file per series per day), so the
  simpler full rebuild is enough and avoids maintaining ingestion-state
  tracking for a project this size.

  payload_json is kept as a raw JSON string (not auto-inferred into a
  struct) purely for auditability/schema-drift detection, since
  single-series and group (CORRA) responses have different shapes.
  observations_flat_json is what silver actually explodes — it's the
  uniform (observation_date, field_name, value_raw) array that
  ingestion/flatten.py already normalized both shapes into, so it parses
  with one fixed schema regardless of which series/group it came from.

  Unions two kinds of landed files at this same one-row-per-file grain:
  daily snapshots (one pull_date per file, under the series_id folders)
  and backfill files (ingestion/backfill.py, under /_backfill/ — one file
  per series covering years of history, so there's no single meaningful
  file-level pull_date; is_backfill=true tells stg_observations.sql to
  derive pull_date per-row from each observation's own date instead).
#}
{% set sql %}
  CREATE OR REPLACE TABLE fmc.bronze.raw_observations AS
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
    '/Volumes/fmc/bronze/raw_valet',
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
    '/Volumes/fmc/bronze/raw_valet/_backfill',
    format => 'text',
    wholeText => true
  )
{% endset %}

{% do run_query(sql) %}
{% do log("Landed bronze files into fmc.bronze.raw_observations", info=True) %}
{% endmacro %}


{% macro land_dq_results_files() %}
{#
  Bridges the Python-side DQ check results (ingestion/land_dq_results.py)
  from /Volumes/fmc/bronze/raw_valet/_dq_results into a queryable table.
  Kept separate from land_bronze_files() because the envelope shape is
  different (a `results` array of check rows, not an observations array).
#}
{% set sql %}
  CREATE OR REPLACE TABLE fmc.bronze.raw_dq_results AS
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
    '/Volumes/fmc/bronze/raw_valet/_dq_results',
    format => 'text',
    wholeText => true
  )
{% endset %}

{% do run_query(sql) %}
{% do log("Landed DQ result files into fmc.bronze.raw_dq_results", info=True) %}
{% endmacro %}
