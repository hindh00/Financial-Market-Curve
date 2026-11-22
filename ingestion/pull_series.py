"""Daily orchestration entrypoint, invoked by .github/workflows/ingest.yml.

Resolves the current RRB benchmark, pulls every registered series plus the
CORRA group, lands each as a snapshot in the Databricks bronze Volume, and
exits non-zero if anything failed — so a gap shows up immediately in the
GitHub Actions run rather than silently disappearing.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from ingestion.config import CORRA_GROUP_NAME, OBSERVATION_WINDOW, SERIES_REGISTRY
from ingestion.databricks_upload import DatabricksConfig, upload_json
from ingestion.flatten import flatten_group_observations, flatten_series_observations
from ingestion.land_dq_results import build_dq_results_for_pull
from ingestion.rrb_lookup import RRBResolutionError, resolve_current_rrb_series
from ingestion.snapshot import build_snapshot, now_utc_iso, snapshot_blob_path, today_et_date
from ingestion.valet_client import ValetAPIError, ValetClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pull_series")


@dataclass
class PullResult:
    series_id: str
    ok: bool
    error: str | None = None


def pull_and_land(client: ValetClient, dbx: DatabricksConfig, pull_date: str) -> list[PullResult]:
    results: list[PullResult] = []

    # Dynamically resolve the RRB benchmark first; its resolution metadata
    # rides along in every RRB snapshot so a future benchmark change is
    # auditable from the landed data itself, not just from this script's logs.
    try:
        rrb = resolve_current_rrb_series(client)
        logger.info("Resolved RRB benchmark: %s (%s)", rrb.series_id, rrb.description)
    except RRBResolutionError as exc:
        logger.error("RRB resolution failed: %s", exc)
        results.append(PullResult(series_id="RRB_LOOKUP", ok=False, error=str(exc)))
        rrb = None

    all_series = dict(SERIES_REGISTRY)
    if rrb is not None:
        all_series[rrb.series_id] = {"category": "rrb_benchmark", "tenor": "LONG", "label": rrb.description}

    single_series_observations: dict[str, list[dict]] = {}
    corra_observations: list[dict] = []

    for series_id in all_series:
        try:
            response = client.get_series_observations(series_id, recent=OBSERVATION_WINDOW)
            single_series_observations[series_id] = response.payload.get("observations", [])
            extra = {"observations_flat": flatten_series_observations(series_id, response.payload)}
            if rrb is not None and series_id == rrb.series_id:
                extra["resolved_as_rrb_benchmark"] = True
                extra["rrb_resolution_timestamp_utc"] = now_utc_iso()
                extra["rrb_description"] = rrb.description
            snapshot = build_snapshot(series_id, response, pull_date=pull_date, extra=extra)
            upload_json(dbx, snapshot_blob_path(series_id, pull_date), snapshot.to_envelope())
            results.append(PullResult(series_id=series_id, ok=True))
            logger.info("Landed %s for pull_date=%s", series_id, pull_date)
        except ValetAPIError as exc:
            logger.error("Failed to pull %s: %s", series_id, exc)
            results.append(PullResult(series_id=series_id, ok=False, error=str(exc)))

    try:
        response = client.get_group_observations(CORRA_GROUP_NAME, recent=OBSERVATION_WINDOW)
        corra_observations = response.payload.get("observations", [])
        extra = {"observations_flat": flatten_group_observations(response.payload)}
        snapshot = build_snapshot(CORRA_GROUP_NAME, response, pull_date=pull_date, extra=extra)
        upload_json(dbx, snapshot_blob_path(CORRA_GROUP_NAME, pull_date), snapshot.to_envelope())
        results.append(PullResult(series_id=CORRA_GROUP_NAME, ok=True))
        logger.info("Landed CORRA group %s for pull_date=%s", CORRA_GROUP_NAME, pull_date)
    except ValetAPIError as exc:
        logger.error("Failed to pull CORRA group %s: %s", CORRA_GROUP_NAME, exc)
        results.append(PullResult(series_id=CORRA_GROUP_NAME, ok=False, error=str(exc)))

    # Python-shaped DQ checks (freshness, schema drift) — see
    # ingestion/land_dq_results.py for why these can't be dbt SQL tests.
    # Landed alongside the data so gold_dq_results.sql can union them with
    # the SQL-shaped checks.
    dq_results = build_dq_results_for_pull(pull_date, single_series_observations, corra_observations)
    dq_envelope = {
        "pull_date": pull_date,
        "pull_timestamp_utc": now_utc_iso(),
        "results": dq_results,
    }
    upload_json(dbx, f"_dq_results/{pull_date}/dq_results_{pull_date}.json", dq_envelope)
    logger.info("Landed %d Python-side DQ results for pull_date=%s", len(dq_results), pull_date)

    return results


def main() -> int:
    pull_date = today_et_date()
    client = ValetClient()
    dbx = DatabricksConfig.from_env()

    results = pull_and_land(client, dbx, pull_date)
    failed = [r for r in results if not r.ok]
    logger.info("Pull summary for %s: %d ok, %d failed", pull_date, len(results) - len(failed), len(failed))
    for r in failed:
        logger.error("  FAILED %s: %s", r.series_id, r.error)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
