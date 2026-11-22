select
    landed_pull_date,
    pull_timestamp_utc,
    check_result.check_name,
    check_result.series_id,
    cast(check_result.observation_date as date) as observation_date,
    cast(check_result.pull_date as date) as pull_date,
    check_result.status,
    check_result.severity,
    check_result.details
from {{ source('bronze', 'raw_dq_results') }}
