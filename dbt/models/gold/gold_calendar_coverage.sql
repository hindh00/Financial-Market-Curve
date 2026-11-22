{#
  Feeds the Data Health page's calendar-coverage heatmap: how many series
  actually have a latest-pull observation for each date, against whether
  that date was a business day/holiday at all.
#}

select
    d.date_day,
    d.is_business_day,
    d.is_holiday,
    d.holiday_name,
    count(distinct f.series_id) as series_observed_count
from {{ ref('dim_date') }} d
left join {{ ref('fact_observation') }} f
    on d.date_day = f.observation_date and f.is_latest_pull
where d.date_day <= current_date()
group by d.date_day, d.is_business_day, d.is_holiday, d.holiday_name
