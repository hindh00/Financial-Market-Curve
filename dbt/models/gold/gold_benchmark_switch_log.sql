{#
  Detects likely benchmark-bond roll days: a tenor whose yield jumps hard
  on a day when the rest of the curve broadly didn't move. That pattern —
  one tenor moving alone, well beyond its typical day-to-day change — is
  more consistent with the on-the-run bond being swapped for a newer issue
  than with an actual market move, which tends to be correlated across
  nearby tenors. This is a heuristic (see the threshold vars in
  dbt_project.yml): calibrate benchmark_switch_abs_threshold against real
  data once enough history exists, and if /lists/series/json ever exposes
  a cleaner issue-level signal for a roll, prefer that instead.

  Deliberately reads from stg_observations (not fact_observation) to avoid
  a circular ref — fact_observation itself joins against this model to set
  is_benchmark_switch_day.
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
