# Money market plumbing

## Dataset
```sql
select observation_date, corra_rate, target_rate, corra_minus_target_bps,
       corra_p05, corra_p25, corra_p75, corra_p95, volume, unique_submitters,
       is_fallback_rate
from fmc.gold.gold_corra_vs_target
order by observation_date
```

## Widgets
- **Combo chart**: line for `corra_minus_target_bps` over `observation_date`, with a shaded band between `corra_p05` and `corra_p95` behind it (Lakeview's area/band chart type, or two area series at p05/p95 with low opacity) and a secondary y-axis bar series for `volume` underneath.
- **Marker layer**: flag days where `is_fallback_rate` is true — a distinct marker color/shape on the line, or a separate thin strip chart beneath the main one.
- **Table** (optional): most recent 10 days with `unique_submitters`, for a quick plumbing-health read alongside the chart.

This is the page the plan's feature 5 is actually about — reproducing,
from public data, the kind of "CORRA Spread to Target and Volume" chart
the Bank itself presents to its market advisory group.
