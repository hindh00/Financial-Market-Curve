# Today

## Datasets
```sql
-- latest_snapshot
select series_id, category, tenor, value, observation_date
from fmc.gold.fact_observation
where is_latest_pull

-- latest_curve
select observation_date, tenor, yield
from fmc.gold.gold_daily_curve

-- freshness_badge
select check_name, status, severity, observation_date
from fmc.gold.gold_dq_results
where check_name = 'corra_freshness'
order by observation_date desc
limit 1
```

## Widgets
- **Counter tiles** (one each): policy rate (`series_id = 'V39079'`), CORRA rate (from `gold_corra_vs_target`, latest `corra_rate`), 2yr yield, 10yr yield, 10s2s spread (from `gold_curve_spread`, latest `spread_10s2s_bps`), USD/CAD (`series_id = 'FXUSDCAD'`).
  - Each tile's comparison value: latest value minus the value as of the most recent `dim_date.is_decision_day` date before today (join `latest_snapshot` to the latest decision date from `fmc.gold.dim_policy_event`).
- **Line chart**: `latest_curve` filtered to today, 1 month ago, and 1 year ago (three series on one tenor-vs-yield line chart) — add a date filter widget bound to three fixed offsets, or three separate queries unioned with a `vintage` label column.
- **Status badge / table**: `freshness_badge` — green if `status = 'pass'`, red if `fail`.
