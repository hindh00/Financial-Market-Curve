"""One-time historical backfill — run manually via workflow_dispatch, never on
the daily schedule. Pulls each series' full history into a separate
/_backfill/ prefix so dashboards aren't empty for months; backfilled rows
can't carry revision history since the historical endpoint only returns
already-settled values.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import date

from ingestion.config import BACKFILL_START_DATE, CORRA_GROUP_NAME, SERIES_REGISTRY
from ingestion.databricks_upload import DatabricksConfig, upload_json
from ingestion.flatten import flatten_group_observations, flatten_series_observations
from ingestion.rrb_lookup import RRBResolutionError, resolve_current_rrb_series
from ingestion.snapshot import backfill_blob_path, build_snapshot
from ingestion.valet_client import ValetAPIError, ValetClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


@dataclass
class BackfillResult:
    series_id: str
    ok: bool
    observation_count: int = 0
    error: str | None = None


def backfill_all(
    client: ValetClient,
    dbx: DatabricksConfig,
    start_date: str = BACKFILL_START_DATE,
    end_date: str | None = None,
) -> list[BackfillResult]:
    end_date = end_date or date.today().isoformat()
    results: list[BackfillResult] = []

    try:
        rrb = resolve_current_rrb_series(client)
        logger.info("Resolved RRB benchmark: %s (%s)", rrb.series_id, rrb.description)
    except RRBResolutionError as exc:
        logger.error("RRB resolution failed, skipping RRB backfill: %s", exc)
        results.append(BackfillResult(series_id="RRB_LOOKUP", ok=False, error=str(exc)))
        rrb = None

    all_series = dict(SERIES_REGISTRY)
    if rrb is not None:
        all_series[rrb.series_id] = {"category": "rrb_benchmark", "tenor": "LONG", "label": rrb.description}

    for series_id in all_series:
        try:
            response = client.get_series_observations(series_id, start_date=start_date, end_date=end_date)
            flat = flatten_series_observations(series_id, response.payload)
            extra = {"observations_flat": flat, "is_backfill": True}
            if rrb is not None and series_id == rrb.series_id:
                extra["resolved_as_rrb_benchmark"] = True
                extra["rrb_description"] = rrb.description
            snapshot = build_snapshot(series_id, response, extra=extra)
            upload_json(dbx, backfill_blob_path(series_id), snapshot.to_envelope())
            results.append(BackfillResult(series_id=series_id, ok=True, observation_count=len(flat)))
            logger.info("Backfilled %s: %d observations (%s to %s)", series_id, len(flat), start_date, end_date)
        except ValetAPIError as exc:
            logger.error("Failed to backfill %s: %s", series_id, exc)
            results.append(BackfillResult(series_id=series_id, ok=False, error=str(exc)))

    try:
        response = client.get_group_observations(CORRA_GROUP_NAME, start_date=start_date, end_date=end_date)
        flat = flatten_group_observations(response.payload)
        extra = {"observations_flat": flat, "is_backfill": True}
        snapshot = build_snapshot(CORRA_GROUP_NAME, response, extra=extra)
        upload_json(dbx, backfill_blob_path(CORRA_GROUP_NAME), snapshot.to_envelope())
        results.append(BackfillResult(series_id=CORRA_GROUP_NAME, ok=True, observation_count=len(flat)))
        logger.info("Backfilled CORRA group %s: %d observations", CORRA_GROUP_NAME, len(flat))
    except ValetAPIError as exc:
        logger.error("Failed to backfill CORRA group %s: %s", CORRA_GROUP_NAME, exc)
        results.append(BackfillResult(series_id=CORRA_GROUP_NAME, ok=False, error=str(exc)))

    return results


def main() -> int:
    client = ValetClient()
    dbx = DatabricksConfig.from_env()
    start_date = os.environ.get("BACKFILL_START_DATE") or BACKFILL_START_DATE

    results = backfill_all(client, dbx, start_date=start_date)
    failed = [r for r in results if not r.ok]
    total_observations = sum(r.observation_count for r in results)
    logger.info(
        "Backfill summary: %d series ok (%d observations total), %d failed",
        len(results) - len(failed), total_observations, len(failed),
    )
    for r in failed:
        logger.error("  FAILED %s: %s", r.series_id, r.error)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
