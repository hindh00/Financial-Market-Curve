"""Normalize Valet API responses into a uniform tall shape at ingestion time.

Single-series and group (e.g. CORRA's CORRA_METRICS) responses have different
JSON shapes — a series response's per-day object has one dynamic key (the
series id), a group response's has several (one per sub-field: the rate
itself, percentiles, volume, ...). Flattening both into the same
(observation_date, field_name, value_raw) shape here, in Python, means
silver's dbt models can explode a single fixed-schema array with
from_json(..., 'array<struct<observation_date:string,field_name:string,value_raw:string>>')
instead of needing dynamic-key JSON parsing in Spark SQL, which has no
clean, version-stable way to handle a field name that varies per row.

The verbatim API payload is still kept in the envelope (snapshot.py) for
auditability and schema-drift detection — this flattened view is an
addition, not a replacement.
"""

from __future__ import annotations

from typing import Any


def flatten_series_observations(series_id: str, payload: dict[str, Any]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for obs in payload.get("observations", []):
        field = obs.get(series_id)
        if not isinstance(field, dict):
            continue
        rows.append({
            "observation_date": obs.get("d"),
            "field_name": series_id,
            "value_raw": field.get("v"),
        })
    return rows


def flatten_group_observations(payload: dict[str, Any]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for obs in payload.get("observations", []):
        observation_date = obs.get("d")
        for key, value in obs.items():
            if key == "d":
                continue
            if isinstance(value, dict) and "v" in value:
                rows.append({
                    "observation_date": observation_date,
                    "field_name": key,
                    "value_raw": value.get("v"),
                })
    return rows
