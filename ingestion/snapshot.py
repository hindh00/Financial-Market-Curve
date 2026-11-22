"""Build the (series_id, pull_date)-keyed snapshot envelope landed into bronze.

Each daily run produces one envelope per series/group containing the raw
API response for a rolling observation window, tagged with the UTC pull
timestamp and an ET pull_date. Snapshots are additive by construction: the
file path downstream (databricks_upload.py) is keyed on pull_date, so a
rerun on the same day overwrites only that day's file and never touches a
prior day's — which is what lets the revision log (feature 3) reconstruct
"what was known on day X" instead of silently losing earlier pulls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ingestion.valet_client import ValetResponse

ET_ZONE = ZoneInfo("America/Toronto")


@dataclass
class Snapshot:
    series_id: str
    pull_date: str  # YYYY-MM-DD, America/Toronto calendar date of the pull
    pull_timestamp_utc: str  # ISO-8601 UTC
    source_url: str
    http_status: int
    payload: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    def to_envelope(self) -> dict[str, Any]:
        """`extra` is expected to carry `observations_flat` — see
        ingestion/flatten.py — which is what silver actually explodes;
        `payload` is kept verbatim alongside it for auditability and
        schema-drift detection."""
        envelope = {
            "series_id": self.series_id,
            "pull_date": self.pull_date,
            "pull_timestamp_utc": self.pull_timestamp_utc,
            "source_url": self.source_url,
            "http_status": self.http_status,
            "payload": self.payload,
        }
        envelope.update(self.extra)
        return envelope


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_et_date() -> str:
    return datetime.now(ET_ZONE).date().isoformat()


def build_snapshot(
    series_id: str,
    response: ValetResponse,
    pull_date: str | None = None,
    pull_timestamp_utc: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Snapshot:
    return Snapshot(
        series_id=series_id,
        pull_date=pull_date or today_et_date(),
        pull_timestamp_utc=pull_timestamp_utc or now_utc_iso(),
        source_url=response.url,
        http_status=response.http_status,
        payload=response.payload,
        extra=extra or {},
    )


def snapshot_blob_path(series_id: str, pull_date: str) -> str:
    """Relative path (under the bronze Volume root) this snapshot lands at.

    Keyed on (series_id, pull_date) only — never on observation_date, since
    one snapshot covers a whole rolling window of observation dates. The
    observation-date grain is created downstream when silver flattens the
    payload's observations array into rows.
    """
    safe_series_id = series_id.replace("/", "_")
    return f"{safe_series_id}/{pull_date}/{safe_series_id}_{pull_date}.json"


def backfill_blob_path(series_id: str) -> str:
    """One fixed path per series (no date in it) — a backfill run overwrites
    its own prior run rather than accumulating one file per historical
    observation. Landed into a separate /_backfill/ prefix so
    land_bronze_files() can tell it apart from daily snapshots (which carry
    one pull_date per file; a backfill file spans years of observation
    dates, so pull_date is derived per-row downstream instead — see
    dbt/models/silver/stg_observations.sql).
    """
    safe_series_id = series_id.replace("/", "_")
    return f"_backfill/{safe_series_id}/{safe_series_id}_backfill.json"
