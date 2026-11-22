# Architecture

```
Bank of Canada Valet API
  -> GitHub Actions (daily cron, Python)        <- only component calling the public internet from outside Databricks
  -> Unity Catalog Volume fmc.bronze.raw_valet   (raw JSON snapshots + pull timestamp)
  -> Databricks Job (sequential tasks, respects the 5-concurrent-task cap):
       1. dbt run-operation land_bronze_files      -> fmc.bronze.raw_observations
          dbt run-operation land_dq_results_files  -> fmc.bronze.raw_dq_results
       2. dbt build   (silver -> gold, incl. dbt tests)
       3. python jobs/pca_curve_factors.py       -> fmc.gold.pca_curve_factors_raw
  -> Databricks AI/BI (Lakeview) Dashboards, 5 pages, in-browser
```

A separate, one-time `ingestion/backfill.py` (`.github/workflows/backfill.yml`,
manual trigger only) pulls each series' full available history into
`/Volumes/fmc/bronze/raw_valet/_backfill/` **before** the daily cron/dbt
chain is ever run for the first time — `land_bronze_files()` reads that
path unconditionally, so it errors if the path doesn't exist yet. See
"Historical backfill" below.

## Why the pull happens in GitHub Actions, not a Databricks notebook
Databricks Free Edition restricts outbound internet from notebooks/jobs to
an unpublished trusted-domain allowlist that will not include
`bankofcanada.ca`. GitHub Actions has no such restriction, and pushing the
landed JSON into the Unity Catalog Volume afterward is an *inbound* call
to Databricks (Files REST API), which the allowlist doesn't affect.

## Naming convention
Catalog `fmc`, schemas `bronze` / `silver` / `gold`. Every gold table that
isn't part of the star schema itself is prefixed `gold_` (e.g.
`gold_daily_curve`) to distinguish it at a glance from `dim_*`/`fact_*`.

## Historical backfill
Without it, every dashboard page starts essentially empty: the daily cron
only pulls a rolling 10-observation window going forward, so "curve vs. 1
year ago," the Decision Days event study, and the CORRA chart would all
take months or years to fill in on their own. `ingestion/backfill.py`
pulls each series' full history in one call (`start_date`/`end_date`
instead of `recent`) and lands it under `/_backfill/` in the Volume —
**run this once, manually, before the first `dbt build`.**

Backfilled rows can't carry revision history: the historical endpoint
returns each date's already-settled value, not what was published on each
day in the past, so revision tracking (feature 3) is only meaningful from
the day the daily cron starts running onward. `stg_observations.sql`
derives `pull_date` per-row from each observation's own date for
backfilled rows (`is_backfill = true`) rather than using a single
file-level `pull_date`, since one backfill file spans years of history.
`gold/dim_date.sql`'s spine starts at `backfill_start_date` (dbt var),
which must match `ingestion/config.py`'s `BACKFILL_START_DATE` — otherwise
backfilled rows before that date fail the referential-integrity DQ check.

## Snapshot design (feature 3 — revision history)
Each daily pull re-fetches a rolling window of the last `OBSERVATION_WINDOW`
observations per series (see `ingestion/config.py`), not just "today's"
value. That's what makes revision detection possible: if a value published
a few days ago gets revised, the next day's pull re-fetches it, lands it
under a new `pull_date`, and `fact_observation`'s window functions detect
the value changed between pulls for the same `observation_date`.
`gold_revision_log.sql` turns that into a human-readable log.

## Benchmark-bond switch detection (feature 2)
`gold_benchmark_switch_log.sql` flags a tenor as having likely rolled to a
new issue when its daily yield change is both large in absolute terms and
far larger than the median move across the rest of the curve that day —
the signature of an idiosyncratic artifact rather than a market-wide
move. This is a heuristic with placeholder thresholds (see
`dbt_project.yml`'s `vars`); calibrate once real data exists, and prefer a
cleaner issue-level signal from `/lists/series/json` if one turns out to
be available once Phase 1 is inspected against the live API.

## RRB benchmark (feature 4)
Never hardcoded — see `ingestion/rrb_lookup.py` and
`dbt/models/gold/dim_series.sql`. The resolved series id rides through
bronze -> silver -> gold with a `is_rrb_benchmark` flag, so
`gold_breakeven_inflation.sql` can label itself from whatever series was
actually resolved, including a caveat about the benchmark's indefinite
aging (issuance ceased in 2022).

## CORRA as a distribution (feature 5)
`stg_corra.sql`'s sub-field names (`AVG.INTWO_P05` etc.) are a best guess
at the live group-observation shape — **verify against a real
`/observations/group/AVG.INTWO/json` response in Phase 1** and correct if
the Bank's actual naming differs. `gold_corra_vs_target.sql`'s fallback-
rate thresholds are similarly placeholders pending real volume data.

## PCA (feature 6)
`jobs/pca_curve_factors.py` runs as a single Databricks Python job task
(not a dbt model — dbt has no linear-algebra primitive), using
`databricks-sql-connector` + numpy SVD rather than assuming a Spark
session is attached to whatever compute runs a serverless Python task.
PC1/PC2/PC3 are labeled level/slope/curvature by convention (typical
loading shapes), not auto-detected. `gold_pca_curve_factors.sql` is a thin
pass-through so it shows up in dbt's lineage/docs.

## dim_policy_event maintenance
There's no Valet series for the decision calendar. `dbt/seeds/
dim_policy_event_seed.csv` currently holds placeholder rows — replace them
with the Bank's verified published "Schedule for Fixed Announcement Dates"
before trusting this table, and re-check it once a year when the Bank
publishes the next year's schedule.

## Optional stretch: Power BI
Not part of the core build (dropped — no Microsoft work/school account
available, and Power BI Desktop has no Mac build). If that changes later,
gold tables can be exported to Parquet, or Power BI Desktop (via a Windows
VM) can DirectQuery the SQL warehouse using Databricks' official Power BI
connector. Nothing in Phases 0-6 depends on this.
