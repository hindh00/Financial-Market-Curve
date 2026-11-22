# Data health

This is the page most portfolio projects skip — showing the DQ checks
actually working, not just the charts they feed.

## Datasets
```sql
-- dq_results
select check_name, observation_date, series_id, tenor, pull_date, status, severity, details
from fmc.gold.gold_dq_results
order by observation_date desc

-- revision_log
select series_id, observation_date, revised_as_of_pull_date, old_value, new_value, delta
from fmc.gold.gold_revision_log
order by revised_as_of_pull_date desc

-- switch_log
select series_id, tenor, observation_date, delta, median_abs_delta_that_day
from fmc.gold.gold_benchmark_switch_log
order by observation_date desc

-- calendar_coverage
select date_day, is_business_day, is_holiday, holiday_name, series_observed_count
from fmc.gold.gold_calendar_coverage
order by date_day
```

## Widgets
- **Filterable table**: `dq_results` — filter control on `status` (pass/fail) and `check_name`; conditionally color the `status` column.
- **Table**: `revision_log` — every detected revision, most recent first.
- **Table**: `switch_log` — every detected benchmark-bond roll day.
- **Heatmap/calendar chart**: `calendar_coverage`, x/y = week/day-of-week or a simple date-ordered strip, color = `series_observed_count` (and a distinct color where `is_holiday` is true, so an expected gap is visually different from an unexpected one).
