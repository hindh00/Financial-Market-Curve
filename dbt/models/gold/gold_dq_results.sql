{#
  Feeds the Data Health page. Unions the SQL-shaped checks (materialized
  as pass/fail rows in dq_checks/) with the Python-shaped checks
  (freshness, schema drift — landed via ingestion/land_dq_results.py,
  flattened in stg_python_dq_results.sql) into one common shape.
#}

select check_name, observation_date, series_id, tenor, pull_date, status, severity, details
from {{ ref('dq_curve_integrity') }}

union all

select check_name, observation_date, series_id, tenor, pull_date, status, severity, details
from {{ ref('dq_holiday_aware_completeness') }}

union all

select check_name, observation_date, series_id, tenor, pull_date, status, severity, details
from {{ ref('dq_referential_integrity') }}

union all

select
    check_name,
    observation_date,
    series_id,
    cast(null as string) as tenor,
    pull_date,
    status,
    severity,
    details
from {{ ref('stg_python_dq_results') }}
