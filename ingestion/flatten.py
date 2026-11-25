"""Normalize Valet API responses into a uniform (observation_date, field_name,
value_raw) shape at ingestion time, since single-series and group responses
have different JSON shapes with dynamic keys Spark SQL can't cleanly parse.
The verbatim payload is still kept in the envelope for auditability; this is
an addition, not a replacement.
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
