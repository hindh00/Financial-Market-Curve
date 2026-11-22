# Databricks Free Edition setup (Phase 0, manual)

This is a one-time, manual setup — nothing here is automated, since it's
account provisioning rather than application code.

## 1. Account
Sign up for Databricks Free Edition at databricks.com. Sign-in is email
OTP, a personal Google account, or a personal Microsoft account — no
organizational/work-school account is required. Confirm you land on one
workspace and one metastore (Free Edition allows exactly one of each).

## 2. Catalog and schemas
In Catalog Explorer, create:
- Catalog: `fmc`
- Schemas: `fmc.bronze`, `fmc.silver`, `fmc.gold`

## 3. Bronze landing volume
Create a managed Unity Catalog Volume: `fmc.bronze.raw_valet`. This is
where GitHub Actions pushes raw JSON snapshots — Volumes hold files, not
queryable tables, so Phase 3 adds a `COPY INTO`/`read_files()` step that
lands these files into a queryable `fmc.bronze.raw_observations` Delta
table before dbt's `source()` can see them.

## 4. SQL warehouse
Free Edition provides exactly one SQL warehouse, fixed at 2X-Small,
serverless. Under SQL Warehouses, open it and note:
- **Server hostname** (also your `DATABRICKS_HOST`, e.g. `https://<workspace>.cloud.databricks.com`)
- **HTTP path** (`DATABRICKS_HTTP_PATH`, needed for dbt's `profiles.yml`)
- **Warehouse ID**

## 5. Access token and GitHub secrets
Generate a personal access token (User Settings → Developer → Access
tokens). In the GitHub repo, add these as **Actions secrets**:

| Secret | Value |
|---|---|
| `DATABRICKS_HOST` | workspace URL, e.g. `https://<workspace>.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | the personal access token |
| `DATABRICKS_VOLUME_PATH` | `/Volumes/fmc/bronze/raw_valet` |
| `DATABRICKS_HTTP_PATH` | the SQL warehouse's HTTP path (used by dbt) |

Also add a repo **variable** `DBT_ENABLED=true` once this phase is done —
`.github/workflows/ci.yml`'s dbt job is gated on it so CI doesn't fail
before there's anything to connect to.

## Constraints to design around (confirmed from the official Free Edition
limitations page, Nov 2026)
- **One SQL warehouse**, 2X-Small only — no size choice, no custom clusters.
- **Max 5 concurrent job tasks per account** — keep Databricks Jobs as a
  small number of *sequential* tasks (e.g. one dbt-build task chained into
  one PCA-job task), never fanned out into many parallel tasks.
- **Outbound internet from notebooks/jobs is restricted** to an
  unpublished trusted-domain allowlist — it will not include
  `bankofcanada.ca`. This is why the Valet API pull happens in GitHub
  Actions, not in a Databricks notebook; Databricks only ever receives
  *inbound* calls (Files API, SQL warehouse connections), which this
  restriction does not affect.
- **No SLA/support guarantee**, and the account **may be deleted after
  prolonged inactivity**. Keep GitHub as the master copy of everything —
  all code, seeds, and dbt models live in this repo and can rebuild the
  Databricks side from scratch if the workspace is ever lost. If you
  expect a long gap between work sessions, log in periodically to reset
  the inactivity clock.
- **R and Scala are unsupported** — everything here is Python/SQL, which
  matches the plan already.

## Verification
- `databricks fs ls dbfs:/Volumes/fmc/bronze/raw_valet` (or Catalog
  Explorer) shows the empty volume.
- A token-authenticated request to the SQL warehouse's HTTP path succeeds
  (e.g. `databricks sql-warehouses get <warehouse-id>`).
