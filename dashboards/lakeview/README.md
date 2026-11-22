# Lakeview dashboard build specs

Lakeview (AI/BI) dashboards are normally built in the Databricks workspace
UI — drag widgets onto a canvas, point each at a query, pick a chart type.
Hand-authoring the underlying `.lvdash.json` risks producing something that
silently fails to import since the schema is versioned and UI-internal;
building through the UI and exporting afterward is the reliable path.

Each file here is a build spec: the dataset query and the widget list for
one page, written against the gold tables from Phase 4/5. Follow these in
the Databricks workspace once gold tables exist (Phase 6), one page at a
time, per the plan's phase ordering:

1. [today.md](today.md)
2. [curve_over_time.md](curve_over_time.md)
3. [decision_days.md](decision_days.md)
4. [money_market_plumbing.md](money_market_plumbing.md)
5. [data_health.md](data_health.md)

After building a page, use **File > Export** (or the dashboard's own
version history) to save its `.lvdash.json` back into this folder so the
dashboard definition is also version-controlled in GitHub, consistent
with keeping GitHub as the master copy of everything (Free Edition has no
support guarantee / backup SLA).
