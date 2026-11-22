"""PCA on daily yield-curve changes — level/slope/curvature factors.

Runs as a single Databricks Job Python task (see docs/architecture.md for
the full job task chain), chained after `dbt build`, never in parallel
with it — Free Edition caps the account at 5 concurrent job tasks, and
there's no reason for this to run concurrently with anything else anyway
since it depends on gold_daily_curve being fresh.

Not a dbt SQL model: dbt has no linear-algebra primitive, and PCA needs
numpy. Uses the Databricks SQL connector (works against the one serverless
SQL warehouse Free Edition provides) rather than assuming a Spark session
is available in whatever compute runs this task — a plain Python
environment is usable either way.

PCA convention: on a yield-curve change matrix, the first three principal
components conventionally correspond to parallel shift ("level"),
flattening/steepening ("slope"), and hump/belly movement ("curvature") —
this is a naming convention based on typical loading shapes, not something
auto-detected per run. Explained-variance ratios are logged on every run as
the built-in sanity check: if the first two components don't explain a
large majority of the variance, something about the input data is off.
"""

from __future__ import annotations

import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pca_curve_factors")

N_COMPONENTS = 3
FACTOR_LABELS = ["level", "slope", "curvature"]
CATALOG_NAME = "financial_market_curve"  # keep in sync with dbt_project.yml's catalog_name var


def _connect():
    from databricks import sql as databricks_sql  # lazy: keeps compute_pca testable without this installed

    return databricks_sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def fetch_daily_curve(conn) -> pd.DataFrame:
    query = f"""
        select observation_date, tenor, yield
        from {CATALOG_NAME}.gold.gold_daily_curve
        where is_benchmark_switch_day = false
        order by observation_date
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["observation_date", "tenor", "yield"])
    return df.pivot(index="observation_date", columns="tenor", values="yield").sort_index()


def compute_pca(wide_yields: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    changes = wide_yields.diff().dropna(how="any")
    if len(changes) < N_COMPONENTS + 1:
        raise ValueError(
            f"Only {len(changes)} complete daily-change rows available — need at least "
            f"{N_COMPONENTS + 1} for a {N_COMPONENTS}-component PCA. Not enough history yet."
        )

    centered = changes - changes.mean(axis=0)
    # SVD-based PCA: columns of Vt.T are the loadings, U*S are the factor scores.
    u, s, vt = np.linalg.svd(centered.to_numpy(), full_matrices=False)
    explained_variance_ratio = (s**2) / np.sum(s**2)

    scores = u[:, :N_COMPONENTS] * s[:N_COMPONENTS]
    factors = pd.DataFrame(
        scores,
        index=changes.index,
        columns=[f"pc{i+1}_{FACTOR_LABELS[i]}" for i in range(N_COMPONENTS)],
    )
    factors.index.name = "observation_date"
    return factors.reset_index(), explained_variance_ratio[:N_COMPONENTS]


def write_factors(conn, factors: pd.DataFrame, explained_variance_ratio: np.ndarray) -> None:
    with conn.cursor() as cursor:
        cursor.execute(f"""
            CREATE OR REPLACE TABLE {CATALOG_NAME}.gold.pca_curve_factors_raw (
                observation_date DATE,
                pc1_level DOUBLE,
                pc2_slope DOUBLE,
                pc3_curvature DOUBLE,
                explained_variance_ratio_pc1 DOUBLE,
                explained_variance_ratio_pc2 DOUBLE,
                explained_variance_ratio_pc3 DOUBLE
            ) USING DELTA
        """)
        rows = [
            (
                row["observation_date"],
                row["pc1_level"],
                row["pc2_slope"],
                row["pc3_curvature"],
                float(explained_variance_ratio[0]),
                float(explained_variance_ratio[1]),
                float(explained_variance_ratio[2]),
            )
            for _, row in factors.iterrows()
        ]
        cursor.executemany(
            f"INSERT INTO {CATALOG_NAME}.gold.pca_curve_factors_raw VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def main() -> int:
    with _connect() as conn:
        wide_yields = fetch_daily_curve(conn)
        try:
            factors, explained_variance_ratio = compute_pca(wide_yields)
        except ValueError as exc:
            logger.warning("Skipping PCA run: %s", exc)
            return 0

        logger.info(
            "Explained variance ratio — PC1 (level): %.1f%%, PC2 (slope): %.1f%%, PC3 (curvature): %.1f%%",
            *(100 * r for r in explained_variance_ratio),
        )
        if sum(explained_variance_ratio[:2]) < 0.5:
            logger.warning(
                "First two components explain only %.1f%% of variance — "
                "lower than typically expected for a yield curve; double-check input data.",
                100 * sum(explained_variance_ratio[:2]),
            )

        write_factors(conn, factors, explained_variance_ratio)
        logger.info("Wrote %d rows to %s.gold.pca_curve_factors_raw", len(factors), CATALOG_NAME)

    return 0


if __name__ == "__main__":
    sys.exit(main())
