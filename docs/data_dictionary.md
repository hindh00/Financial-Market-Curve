# Data dictionary (gold layer)

## Star schema
| Table | Grain | Key columns |
|---|---|---|
| `dim_series` | one row per series_id | series_id, category, tenor, instrument_type, unit, label |
| `dim_date` | one row per calendar day | date_day, is_weekend, is_holiday, is_business_day, is_decision_day, decision_action, decision_size_bps |
| `dim_policy_event` | one row per decision date | decision_date, action (cut/hold/hike), size_bps, has_mpr, notes |
| `fact_observation` | series_id x observation_date x pull_date | value, is_latest_pull, is_revision, is_benchmark_switch_day, is_backfill |

## Dashboard-ready gold tables
| Table | Feeds | Notes |
|---|---|---|
| `gold_daily_curve` | Today, Curve over time | long format: observation_date x tenor x yield |
| `gold_curve_spread` | Curve over time | 10s2s spread in bps + is_inverted |
| `gold_decision_day_reactions` | Decision days | every decision incl. holds, joined to same-day 2y/10y/USDCAD moves (switch-day artifacts nulled out) |
| `gold_corra_vs_target` | Money market plumbing | CORRA-minus-target bps, 5th-95th percentile band, volume, is_fallback_rate |
| `gold_breakeven_inflation` | (supporting) | nominal-minus-real yield, with a caveat_text column about the aging RRB benchmark |
| `gold_benchmark_switch_log` | Data health | detected bond-roll days per tenor |
| `gold_revision_log` | Data health | old_value -> new_value, keyed on which pull_date surfaced the change |
| `gold_dq_results` | Data health | unions SQL-shaped + Python-shaped DQ checks, one row per check per entity |
| `gold_calendar_coverage` | Data health | business-day/holiday status x how many series were actually observed |
| `gold_pca_curve_factors` | Curve over time | level/slope/curvature factor scores, written by jobs/pca_curve_factors.py |

## Known placeholders to replace before trusting the numbers
- `dbt/seeds/dim_policy_event_seed.csv` — sample rows, not the Bank's verified schedule.
- `dbt/models/silver/stg_corra.sql` — CORRA sub-field names are a best guess, unverified against a live API response.
- `dbt_project.yml` vars `benchmark_switch_abs_threshold`, `corra_fallback_volume_threshold`, `corra_fallback_submitter_threshold` — heuristic thresholds pending calibration against real data.
