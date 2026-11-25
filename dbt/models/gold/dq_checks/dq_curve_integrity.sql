{#
  Every active benchmark-bond tenor should exist for every business day
  so far. Materializes the same check as dbt/tests/assert_curve_completeness.sql
  as pass/fail rows, so Data Health can show history, not just build status.
#}

with business_days as (
    select date_day
    from {{ ref('dim_date') }}
    where is_business_day and date_day <= current_date()
),

expected_tenors as (
    select distinct tenor
    from {{ ref('dim_series') }}
    where category = 'benchmark_bond' and tenor is not null
),

expected as (
    select b.date_day, t.tenor
    from business_days b
    cross join expected_tenors t
),

observed as (
    select distinct observation_date, tenor
    from {{ ref('fact_observation') }}
    where category = 'benchmark_bond' and is_latest_pull
)

select
    'curve_integrity' as check_name,
    e.date_day as observation_date,
    cast(null as string) as series_id,
    e.tenor,
    cast(null as date) as pull_date,
    case when o.tenor is null then 'fail' else 'pass' end as status,
    'high' as severity,
    concat('Missing ', e.tenor, ' benchmark bond yield on ', e.date_day) as details
from expected e
left join observed o
    on e.date_day = o.observation_date and e.tenor = o.tenor
