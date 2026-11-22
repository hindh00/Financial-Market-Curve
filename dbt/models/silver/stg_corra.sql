{#
  CORRA's group response carries several named sub-fields per day (the
  rate itself, percentiles, volume, unique submitters). This pivots those
  into named columns per (observation_date, pull_date).

  CAVEAT: the exact sub-field names below (AVG.INTWO_P05/P25/P75/P95,
  AVG.INTWO_VOLUME, AVG.INTWO_SUBMITTERS) are this project's best guess at
  the live Valet group-observation naming convention, based on the group
  label pattern, and have NOT been verified against a real API response —
  do that in Phase 1 (hit /observations/group/AVG.INTWO/json directly and
  inspect the actual field names) and correct the CASE expressions below
  if they differ before trusting this model.
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
    where series_id = 'AVG.INTWO'
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
    max(case when field_name = 'AVG.INTWO_P05' then value end) as corra_p05,
    max(case when field_name = 'AVG.INTWO_P25' then value end) as corra_p25,
    max(case when field_name = 'AVG.INTWO_P75' then value end) as corra_p75,
    max(case when field_name = 'AVG.INTWO_P95' then value end) as corra_p95,
    max(case when field_name = 'AVG.INTWO_VOLUME' then value end) as volume,
    max(case when field_name = 'AVG.INTWO_SUBMITTERS' then value end) as unique_submitters
from parsed
group by observation_date, pull_date, pull_timestamp_utc
