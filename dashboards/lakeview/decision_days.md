# Decision days

## Datasets
```sql
-- decisions
select decision_date, action, size_bps, has_mpr, change_2y, change_10y,
       usdcad_change, reaction_excludes_switch_artifact
from fmc.gold.gold_decision_day_reactions
order by decision_date desc

-- curve_around_decision (parameterized by a clicked decision_date)
select observation_date, tenor, yield
from fmc.gold.gold_daily_curve
where observation_date between :decision_date - interval 5 days
                          and :decision_date + interval 5 days
```

## Widgets
- **Table**: `decisions` — every decision including holds (size_bps = 0), with has_mpr as a badge/icon column.
- **Scatter chart**: `decisions`, x = size_bps, y = change_2y. Points far from the trend line (holds that moved the 2yr a lot, or cuts that moved it little) are the "surprises" — add a trend/regression line if Lakeview's scatter widget supports one, or color points by `abs(change_2y)` to make outliers visually pop.
- **Drill-through**: wire a click on a `decisions` table row to set a dashboard filter parameter (`decision_date`), which `curve_around_decision` consumes to show the curve for days immediately before/after that decision.
- Rows where `reaction_excludes_switch_artifact` is true should show a small note/icon that a reaction value was excluded due to a detected benchmark switch that day.
