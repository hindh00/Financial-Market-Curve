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
| `gold_dq_results` | Data health | unions 4 SQL-shaped checks (curve integrity, holiday-aware completeness, referential integrity, jump check) + Python-shaped checks (freshness, schema drift), one row per check per entity |
| `gold_calendar_coverage` | Data health | business-day/holiday status x how many series were actually observed |
| `gold_pca_curve_factors` | Curve over time | level/slope/curvature factor scores, written by jobs/pca_curve_factors.py |

## Known placeholders to replace before trusting the numbers
- `dbt_project.yml` var `benchmark_switch_abs_threshold` (0.15) — the only
  remaining guessed threshold. No clean API signal exists for "a specific
  benchmark bond was swapped on this date" (the Bank publishes forward
  maturity schedules, not a retroactive switch-date feed), so this stays a
  statistical heuristic to calibrate once enough live yield history exists.
- `dbt_project.yml` var `jump_threshold_std` (4.0 robust z-score) — a
  generic statistical convention, not a Bank-specific fact, so there's
  nothing to "verify" here — just a threshold you may want to tune once
  you see how noisy real yield moves are. Now live: `dq_jump_check.sql`
  flags single-day outlier moves per series using this threshold
  (benchmark-switch days excluded, since `gold_benchmark_switch_log.sql`
  already explains those).

## Verified against the live API (2026-11-22)
- CORRA is published as group `CORRA_METRICS` (not `AVG.INTWO` — that's the
  rate sub-series' id within the group). `stg_corra.sql`'s field names are
  confirmed against a real `/observations/group/CORRA_METRICS/json` response.
- The RRB benchmark resolves to `BD.CDN.RRB.DQ.YLD` ("Real Return Bonds
  yield, long-term") — Valet doesn't expose individual-bond-level RRB
  series the way the plan originally assumed; it only ever publishes one
  blended long-term RRB yield, parallel to `BD.CDN.LONG.DQ.YLD` for
  nominal bonds. `RRB_DESCRIPTION_PATTERN` in `ingestion/config.py` is
  narrowed to match it uniquely.
- CORRA's fallback-rate trigger is **volume-only** per the Bank's own
  published methodology (bankofcanada.ca/rates/interest-rates/corra/
  methodology-calculating-corra/) — submitter count is not part of it.
  `gold_corra_vs_target.sql` now compares two real published numbers
  (`CORRA_TRIMMED_VOLUME` vs. `CORRA_MINIMUM_VOLUME_THRESHOLD`) instead of
  a guessed constant; the old `corra_fallback_volume_threshold` /
  `corra_fallback_submitter_threshold` vars are removed.
- `dim_policy_event_seed.csv` is fully populated and verified (see
  `dim_policy_event.sql`'s header) — no longer a placeholder.
