{#
  Heuristic: flags a tenor whose yield jumps hard alone while the rest of
  the curve doesn't move, which looks more like a bond roll than a market
  move. Reads from stg_observations, not fact_observation, to avoid a
  circular ref (fact_observation joins against this to set
  is_benchmark_switch_day).
#}

with tenor_values as (
    select series_id, tenor, observation_date, pull_date, value
    from {{ ref('stg_observations') }}
    where category = 'benchmark_bond' and tenor is not null
),

latest_per_day as (
    select * from (
        select
            *,
            row_number() over (partition by series_id, observation_date order by pull_date desc) as rn
        from tenor_values
    )
    where rn = 1
),

changes as (
    select
        series_id,
        tenor,
        observation_date,
        value,
        value - lag(value) over (partition by series_id order by observation_date) as delta
    from latest_per_day
),

day_level_stats as (
    select
        observation_date,
        percentile_approx(abs(delta), 0.5) as median_abs_delta_that_day
    from changes
    where delta is not null
    group by observation_date
)

select
    c.series_id,
    c.tenor,
    c.observation_date,
    c.delta,
    d.median_abs_delta_that_day,
    true as is_switch_day
from changes c
join day_level_stats d
    on c.observation_date = d.observation_date
where
    abs(c.delta) > {{ var('benchmark_switch_abs_threshold') }}
    and abs(c.delta) > 3 * d.median_abs_delta_that_day
