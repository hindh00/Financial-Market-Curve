# Curve over time

## Datasets
```sql
-- curve_heatmap
select observation_date, tenor, yield, is_benchmark_switch_day
from fmc.gold.gold_daily_curve

-- spread
select observation_date, spread_10s2s_bps, is_inverted
from fmc.gold.gold_curve_spread

-- pca_factors
select observation_date, pc1_level, pc2_slope, pc3_curvature
from fmc.gold.gold_pca_curve_factors
```

## Widgets
- **Heatmap**: `curve_heatmap`, x = observation_date, y = tenor (ordered 60D..LONG, not alphabetically — set an explicit category order), color = yield. Consider a marker/border on cells where `is_benchmark_switch_day` is true, so a roll is visibly distinguished from an actual rate move.
- **Line chart**: `spread`, x = observation_date, y = spread_10s2s_bps. Shade/band the background wherever `is_inverted` is true (Lakeview supports conditional reference bands/shapes on a line chart — configure a secondary series or annotation layer for the inverted ranges).
- **Line chart**: `pca_factors`, three lines (pc1_level, pc2_slope, pc3_curvature) over observation_date.
