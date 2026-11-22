{#
  A gap on a business day is an error; a gap on a weekend/holiday is
  expected (and not checked here at all, since `business_days` already
  excludes them). Scoped to fact_observation's series — CORRA's
  completeness is implicitly covered by stg_corra/gold_corra_vs_target
  having a row for the day, not checked separately here.
#}

with business_days as (
    select date_day
    from {{ ref('dim_date') }}
    where is_business_day and date_day <= current_date()
),

tracked_series as (
    select distinct series_id
    from {{ ref('dim_series') }}
    where category != 'corra'
),

expected as (
    select b.date_day, s.series_id
    from business_days b
    cross join tracked_series s
),

observed as (
    select distinct observation_date, series_id
    from {{ ref('fact_observation') }}
    where is_latest_pull
)

select
    'holiday_aware_completeness' as check_name,
    e.date_day as observation_date,
    e.series_id,
    cast(null as string) as tenor,
    cast(null as date) as pull_date,
    case when o.series_id is null then 'fail' else 'pass' end as status,
    'high' as severity,
    concat('Missing observation for ', e.series_id, ' on ', e.date_day) as details
from expected e
left join observed o
    on e.date_day = o.observation_date and e.series_id = o.series_id
