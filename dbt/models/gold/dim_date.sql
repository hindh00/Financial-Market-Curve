{#
  The calendar spine is a pure construct (no raw data to type), so it's
  built directly here rather than in silver — there's nothing silver would
  add. Decision-day flags join in from dim_policy_event, which is why this
  lives in gold rather than silver.

  start_date matches backfill_start_date (dbt_project.yml vars), which
  must itself match ingestion/config.py's BACKFILL_START_DATE — otherwise
  backfilled fact rows before this spine's start would have no dim_date
  row to join to and fail the referential-integrity DQ check.
#}

with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ var('backfill_start_date') ~ "' as date)",
        end_date="dateadd(year, 1, current_date())"
    ) }}
),

holidays as (
    select holiday_date, holiday_name
    from {{ ref('canadian_holidays_seed') }}
),

calendar as (
    select
        cast(spine.date_day as date) as date_day,
        dayofweek(spine.date_day) in (1, 7) as is_weekend, -- Spark dayofweek: Sunday=1 .. Saturday=7
        holidays.holiday_name is not null as is_holiday,
        holidays.holiday_name,
        (dayofweek(spine.date_day) not in (1, 7)) and holidays.holiday_name is null as is_business_day
    from spine
    left join holidays
        on cast(spine.date_day as date) = holidays.holiday_date
)

select
    c.date_day,
    c.is_weekend,
    c.is_holiday,
    c.holiday_name,
    c.is_business_day,
    (p.decision_date is not null) as is_decision_day,
    p.action as decision_action,
    p.size_bps as decision_size_bps
from calendar c
left join {{ ref('dim_policy_event') }} p
    on c.date_day = p.decision_date
