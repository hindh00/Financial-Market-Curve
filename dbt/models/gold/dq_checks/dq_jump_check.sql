{#
  Mirrors ingestion/dq_checks.py's check_jump(): a median/MAD robust
  z-score (resistant to the outlier inflating its own baseline), excluding
  benchmark-switch days entirely since gold_benchmark_switch_log.sql
  already explains those. Materialized as one row per computable
  day-over-day change, not just failures, so Data Health shows full history.
#}

with latest_per_day as (
    select
        series_id,
        observation_date,
        pull_date,
        value,
        row_number() over (
            partition by series_id, observation_date order by pull_date desc
        ) as rn
    from {{ ref('stg_observations') }}
    where value is not null
),

deduped as (
    select series_id, observation_date, pull_date, value
    from latest_per_day
    where rn = 1
),

changes as (
    select
        d.series_id,
        d.observation_date,
        d.pull_date,
        d.value - lag(d.value) over (partition by d.series_id order by d.observation_date) as delta,
        coalesce(bsl.is_switch_day, false) as is_benchmark_switch_day
    from deduped d
    left join {{ ref('gold_benchmark_switch_log') }} bsl
        on d.series_id = bsl.series_id and d.observation_date = bsl.observation_date
),

non_switch_changes as (
    select series_id, observation_date, pull_date, delta
    from changes
    where delta is not null and not is_benchmark_switch_day
),

series_median as (
    select series_id, percentile_approx(delta, 0.5) as median_delta
    from non_switch_changes
    group by series_id
),

abs_deviation as (
    select
        c.series_id,
        c.observation_date,
        c.pull_date,
        c.delta,
        abs(c.delta - m.median_delta) as abs_dev
    from non_switch_changes c
    join series_median m on c.series_id = m.series_id
),

series_mad as (
    select series_id, percentile_approx(abs_dev, 0.5) as mad
    from abs_deviation
    group by series_id
)

select
    'jump_check' as check_name,
    a.observation_date,
    a.series_id,
    cast(null as string) as tenor,
    a.pull_date,
    case
        when (a.abs_dev / (sm.mad / 0.6745)) > {{ var('jump_threshold_std') }} then 'fail'
        else 'pass'
    end as status,
    'medium' as severity,
    concat(
        'Day-over-day change of ', round(a.delta, 4),
        ' is a ', round(a.abs_dev / (sm.mad / 0.6745), 1),
        'x robust z-score move for ', a.series_id, ' on ', a.observation_date
    ) as details
from abs_deviation a
join series_mad sm on a.series_id = sm.series_id
where sm.mad > 0
