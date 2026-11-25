# Architecture

```
Bank of Canada Valet API
  -> GitHub Actions (daily cron, Python)        <- only component calling the public internet from outside Databricks
  -> Unity Catalog Volume financial_market_curve.bronze.raw_valet   (raw JSON snapshots + pull timestamp)
  -> Databricks Job (sequential tasks, respects the 5-concurrent-task cap):
       1. dbt run-operation land_bronze_files      -> financial_market_curve.bronze.raw_observations
          dbt run-operation land_dq_results_files  -> financial_market_curve.bronze.raw_dq_results
       2. dbt build --exclude gold_pca_curve_factors   (silver -> gold, incl. dbt tests)
       3. python jobs/pca_curve_factors.py       -> financial_market_curve.gold.pca_curve_factors_raw
       4. dbt run --select gold_pca_curve_factors      (thin pass-through, same-day freshness)
  -> Databricks AI/BI (Lakeview) Dashboards, 5 pages, in-browser
```

A separate, one-time `ingestion/backfill.py` (`.github/workflows/backfill.yml`,
manual trigger only) pulls each series' full available history into
`/Volumes/financial_market_curve/bronze/raw_valet/_backfill/` **before** the daily cron/dbt
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
Catalog `financial_market_curve` (set via dbt's `catalog_name` var —
`dbt/dbt_project.yml` — and `CATALOG_NAME` in `jobs/pca_curve_factors.py`;
change it in exactly those two places if you ever rename the catalog),
schemas `bronze` / `silver` / `gold`. Every gold table that
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
aging (issuance ceased in 2022). Verified against the live API
(2026-11-22): Valet doesn't expose individual-bond-level RRB series the
way the original plan assumed — it only ever publishes one blended
long-term yield, `BD.CDN.RRB.DQ.YLD`, parallel to `BD.CDN.LONG.DQ.YLD` for
nominal bonds. `RRB_DESCRIPTION_PATTERN` is narrowed (`"real return bonds?
yield"`) to resolve to it uniquely instead of the 15 loosely-related
series ("real return bond" alone also matches index ratios, CPI
reference dates, and asset-holding series).

## CORRA as a distribution (feature 5)
CORRA publishes under group `CORRA_METRICS` (not `AVG.INTWO` — that's the
id of the rate sub-series *within* the group, not the group's own name).
`stg_corra.sql`'s field names are verified against a real
`/observations/group/CORRA_METRICS/json` response (2026-11-22).
`gold_corra_vs_target.sql`'s `is_fallback_rate` is no longer a guessed
threshold: per the Bank's published methodology (bankofcanada.ca/rates/
interest-rates/corra/methodology-calculating-corra/), fallback triggers
purely on trimmed volume falling below a minimum threshold — itself
defined as `max($3B, 30% of the trailing 5-day average trimmed volume)` —
submitter count is not part of the Bank's own trigger. The Bank publishes
that day's resolved threshold directly as `CORRA_MINIMUM_VOLUME_THRESHOLD`,
so the gold model just compares two real published numbers.

## PCA (feature 6)
`jobs/pca_curve_factors.py` runs as a single Databricks Python job task
(not a dbt model — dbt has no linear-algebra primitive), using
`databricks-sql-connector` + numpy SVD rather than assuming a Spark
session is attached to whatever compute runs a serverless Python task.
PC1/PC2/PC3 are labeled level/slope/curvature by convention (typical
loading shapes), not auto-detected. `gold_pca_curve_factors.sql` is a thin
pass-through so it shows up in dbt's lineage/docs.

Chicken-and-egg: the pass-through model reads `gold.pca_curve_factors_raw`,
which the PCA task only writes *after* the main `dbt build` — so the main
build always runs with `--exclude gold_pca_curve_factors`, and a final
`dbt run --select gold_pca_curve_factors` task (step 4 above) materializes
it same-day once the PCA task has run. Without that 4th task, the
pass-through would always be a day stale (built from yesterday's PCA
output) or fail outright on a workspace that's never run the PCA task yet.

The PCA task needs `DATABRICKS_HOST`/`DATABRICKS_HTTP_PATH`/
`DATABRICKS_TOKEN` as task environment variables even though it runs
inside Databricks — it deliberately goes through `databricks-sql-connector`
rather than a Spark session (see the module docstring), so it still needs
a token the same way the GitHub Actions ingestion job does. Store the
token as a Databricks secret (`databricks secrets create-scope` /
`put-secret`) and reference it from the task config as
`{{secrets/<scope>/<key>}}` rather than pasting it in plaintext — reuse the
same token already proven to work for the GitHub Actions Jobs API trigger,
since freshly-generated PATs get rejected outright on this workspace (see
`SESSION_LOG.md`'s 2026-11-23 entry).

## dim_policy_event maintenance
There's no Valet series for the decision calendar, so `dbt/seeds/
dim_policy_event_seed.csv` is manually compiled (81 rows, 2017-01-18
through 2026-10-28) from the Bank's "Schedule for Fixed Announcement
Dates" press releases and individual decision releases — never derived
from V39079 rate changes, which would silently drop every hold. Verified
by replaying `action`/`size_bps` cumulatively against the known overnight
rate path (0.50% start-2017 -> 1.75% end-2018 -> 0.25% COVID low -> 5.00%
mid-2023 peak -> 2.25% late-2025 -> 2.50% after the 2026-10-28 hike — all
checkpoints match). The three March 2020 COVID-era cuts (03-04 scheduled,
03-13 and 03-27 unscheduled inter-meeting) use the Bank's *announcement*
date, not the settlement/effective date Valet reports (pre-2021, these
were same-day; from 2021 on, effective date is one business day later) —
see the per-row `notes` column for the unscheduled ones. Needs a yearly
top-up once the Bank publishes next year's schedule (usually each July).

## Optional stretch: Power BI
Not part of the core build (dropped — no Microsoft work/school account
available, and Power BI Desktop has no Mac build). If that changes later,
gold tables can be exported to Parquet, or Power BI Desktop (via a Windows
VM) can DirectQuery the SQL warehouse using Databricks' official Power BI
connector. Nothing in Phases 0-6 depends on this.
