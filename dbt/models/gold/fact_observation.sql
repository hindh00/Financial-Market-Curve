{#
  Central fact: one row per (series_id, observation_date, pull_date).
  is_latest_pull marks the most-recently-pulled value for that
  observation_date (what "today's curve" should use); is_revision flags
  when a pull changed the value from what the prior pull had recorded for
  the same observation_date (feature 3 — see gold_revision_log.sql for the
  human-readable log built on top of this flag).
#}

with windowed as (
    select
        *,
        row_number() over (
            partition by series_id, observation_date
            order by pull_date desc, pull_timestamp_utc desc
        ) as pull_rank,
        lag(value) over (
            partition by series_id, observation_date
            order by pull_date, pull_timestamp_utc
        ) as prior_pull_value
    from {{ ref('stg_observations') }}
)

select
    w.series_id,
    w.observation_date,
    w.pull_date,
    w.pull_timestamp_utc,
    w.value,
    w.value_raw,
    w.has_revision_marker,
    w.is_backfill,
    w.is_rrb_benchmark,
    w.category,
    w.tenor,
    w.instrument_type,
    w.unit,
    w.label,
    (w.pull_rank = 1) as is_latest_pull,
    (w.prior_pull_value is not null and w.prior_pull_value != w.value) as is_revision,
    coalesce(bsl.is_switch_day, false) as is_benchmark_switch_day
from windowed w
left join {{ ref('gold_benchmark_switch_log') }} bsl
    on w.series_id = bsl.series_id and w.observation_date = bsl.observation_date
