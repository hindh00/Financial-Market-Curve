# Financial Market Curve

A Bank of Canada Valet API data pipeline and dashboard answering three
market-structure questions, plus a Data Health page showing the DQ checks
that most portfolio projects skip:

1. **What were markets expecting?** The yield curve, and how far the
   2-year yield sits from the policy rate.
2. **Did the Bank surprise them?** An event study of every decision day
   (holds included).
3. **Did the policy rate reach the money market?** CORRA vs. the target
   rate, shown as a distribution, not a single line.

## Architecture

```
Bank of Canada Valet API
  -> GitHub Actions (daily cron, Python)
  -> Unity Catalog Volume (bronze, raw JSON + pull timestamp)
  -> dbt on a Databricks SQL warehouse (silver -> gold, star schema + DQ results)
  -> a Databricks Python job (PCA)
  -> Databricks AI/BI (Lakeview) Dashboards, 5 pages
```

See [docs/architecture.md](docs/architecture.md) for why each piece is
where it is, and [docs/data_dictionary.md](docs/data_dictionary.md) for
the gold-layer tables.

## Getting started

1. **Phase 0** — [docs/setup_databricks_free_edition.md](docs/setup_databricks_free_edition.md): one-time Databricks account/catalog/warehouse setup, then add the resulting secrets to this repo's GitHub Actions settings.
2. **Phase 1-2** — the ingestion pipeline and its tests already work with no cloud account: `pip install -r requirements-dev.txt && pytest tests/ -v`.
3. **Historical backfill (run once, before step 4)** — trigger `.github/workflows/backfill.yml` manually (or `python -m ingestion.backfill`) to pull each series' full history, so the dashboards aren't empty for months. `land_bronze_files()` reads this path unconditionally, so it must exist before the first dbt build.
4. **Turn on the daily cron** — once secrets exist, trigger `.github/workflows/ingest.yml` manually once to confirm it lands data, then let the daily schedule take over.
5. **Phase 3-5** — `dbt/` builds silver/gold against your warehouse (`cd dbt && dbt seed && dbt run-operation land_bronze_files && dbt run-operation land_dq_results_files && dbt build`).
6. **Phase 6** — build the dashboards in the Databricks workspace UI following [dashboards/lakeview/](dashboards/lakeview/).

## Repo layout

- `ingestion/` — the Valet API pull, run daily by `.github/workflows/ingest.yml`.
- `tests/` — pytest for the ingestion layer (no live network calls, no cloud account needed).
- `dbt/` — silver/gold transforms, seeds, and DQ tests.
- `jobs/` — the PCA Python job (not expressible in dbt SQL).
- `dashboards/lakeview/` — build specs for the 5 dashboard pages.
- `docs/` — setup, architecture, and data dictionary.

## Known placeholders

A few things are deliberately left as placeholders pending real data or
manual verification — see the "Known placeholders" section of
[docs/data_dictionary.md](docs/data_dictionary.md) before trusting the
numbers end to end.
