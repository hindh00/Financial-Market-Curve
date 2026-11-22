{#
  CORRA-minus-target in bps, plus the percentile band and volume Lakeview's
  "Money market plumbing" page charts. is_fallback_rate flags days where
  volume/submitter counts are too thin for CORRA to be calculated from
  actual trades (the Bank falls back to a fixed rate on those days) —
  thresholds are placeholders, see the note in dbt_project.yml's vars.
#}

with corra as (
    select
        observation_date,
        pull_date,
        corra_rate,
        corra_p05,
        corra_p25,
        corra_p75,
        corra_p95,
        volume,
        unique_submitters,
        row_number() over (partition by observation_date order by pull_date desc) as pull_rank
    from {{ ref('stg_corra') }}
),

latest_corra as (
    select * from corra where pull_rank = 1
),

target as (
    select observation_date, value as target_rate
    from {{ ref('fact_observation') }}
    where series_id = 'V39079' and is_latest_pull
)

select
    lc.observation_date,
    lc.corra_rate,
    t.target_rate,
    (lc.corra_rate - t.target_rate) * 100 as corra_minus_target_bps,
    lc.corra_p05,
    lc.corra_p25,
    lc.corra_p75,
    lc.corra_p95,
    lc.volume,
    lc.unique_submitters,
    (
        lc.volume < {{ var('corra_fallback_volume_threshold') }}
        or lc.unique_submitters < {{ var('corra_fallback_submitter_threshold') }}
    ) as is_fallback_rate
from latest_corra lc
left join target t
    on lc.observation_date = t.observation_date
