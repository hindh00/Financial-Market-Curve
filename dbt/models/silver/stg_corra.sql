{#
  CORRA publishes via the CORRA_METRICS group, not a bare series — the
  group bundles the rate ("AVG.INTWO") plus volume and percentile metrics.
#}

with exploded as (
    select
        pull_date,
        pull_timestamp_utc,
        explode(
            from_json(
                observations_flat_json,
                'array<struct<observation_date:string,field_name:string,value_raw:string>>'
            )
        ) as obs
    from {{ source('bronze', 'raw_observations') }}
    where series_id = 'CORRA_METRICS'
),

parsed as (
    select
        cast(obs.observation_date as date) as observation_date,
        pull_date,
        pull_timestamp_utc,
        obs.field_name,
        try_cast(obs.value_raw as double) as value
    from exploded
)

select
    observation_date,
    pull_date,
    pull_timestamp_utc,
    max(case when field_name = 'AVG.INTWO' then value end) as corra_rate,
    max(case when field_name = 'CORRA_RATE_AT_PERCENTILE_5' then value end) as corra_p05,
    max(case when field_name = 'CORRA_RATE_AT_PERCENTILE_25' then value end) as corra_p25,
    max(case when field_name = 'CORRA_RATE_AT_PERCENTILE_75' then value end) as corra_p75,
    max(case when field_name = 'CORRA_RATE_AT_PERCENTILE_95' then value end) as corra_p95,
    max(case when field_name = 'CORRA_TRIMMED_VOLUME' then value end) as volume,
    max(case when field_name = 'CORRA_MINIMUM_VOLUME_THRESHOLD' then value end) as min_volume_threshold,
    max(case when field_name = 'CORRA_NUMBER_OF_SUBMITTERS' then value end) as unique_submitters
from parsed
group by observation_date, pull_date, pull_timestamp_utc
