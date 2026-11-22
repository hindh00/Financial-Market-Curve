{#
  Every decision (holds included) joined to the same-day move in the 2yr
  and 10yr yields and USD/CAD. change_2y/change_10y are nulled out (not
  just flagged) when that day was also flagged as a benchmark-switch day
  for that tenor — a bond roll isn't a market reaction to the decision, so
  it shouldn't count as one in the scatter/outlier chart on the Decision
  Days page. reaction_excludes_switch_artifact records when that happened
  so the dashboard can show it was excluded rather than just showing a gap.
#}

with yields as (
    select
        observation_date,
        series_id,
        tenor,
        value,
        is_benchmark_switch_day,
        value - lag(value) over (partition by series_id order by observation_date) as daily_change
    from {{ ref('fact_observation') }}
    where category in ('benchmark_bond', 'treasury_bill')
        and is_latest_pull
),

fx as (
    select
        observation_date,
        value - lag(value) over (order by observation_date) as usdcad_change
    from {{ ref('fact_observation') }}
    where series_id = 'FXUSDCAD' and is_latest_pull
)

select
    d.decision_date,
    d.action,
    d.size_bps,
    d.has_mpr,
    case when y2.is_benchmark_switch_day then null else y2.daily_change end as change_2y,
    case when y10.is_benchmark_switch_day then null else y10.daily_change end as change_10y,
    fx.usdcad_change,
    coalesce(y2.is_benchmark_switch_day, false) or coalesce(y10.is_benchmark_switch_day, false) as reaction_excludes_switch_artifact
from {{ ref('dim_policy_event') }} d
left join yields y2
    on y2.observation_date = d.decision_date and y2.tenor = '2Y'
left join yields y10
    on y10.observation_date = d.decision_date and y10.tenor = '10Y'
left join fx
    on fx.observation_date = d.decision_date
