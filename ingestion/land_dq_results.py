"""Runs the Python-side DQ checks (freshness, schema drift) at pull time and
lands their results into the Volume alongside the data, so dbt's
gold_dq_results.sql can union them with the SQL-shaped checks (curve
integrity, holiday-aware completeness, referential integrity — those stay
dbt tests since they're naturally SQL-shaped).

Called from pull_series.py once per daily run, after all series/group
pulls — it has everything it needs from what was already fetched this run,
without re-downloading anything.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ingestion.dq_checks import check_corra_freshness, check_schema_drift

EXPECTED_SINGLE_SERIES_KEYS = {"d"}  # plus the series_id itself, added per-call


def check_single_series_schema(series_id: str, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each observation object should have exactly {"d", <series_id>} as
    top-level keys. Anything else is a schema-drift signal."""
    expected = EXPECTED_SINGLE_SERIES_KEYS | {series_id}
    results = []
    for obs in observations:
        result = check_schema_drift(series_id, prior_fields=expected, new_fields=set(obs.keys()))
        if result is not None:
            result["observation_date"] = obs.get("d")
            results.append(result)
    return results


def check_corra_freshness_for_pull(pull_date_str: str, corra_observations: list[dict[str, Any]], holidays: set[date] | None = None) -> list[dict[str, Any]]:
    pull_date = date.fromisoformat(pull_date_str)
    results = []
    for obs in corra_observations:
        d = obs.get("d")
        if not d:
            continue
        observation_date = date.fromisoformat(d)
        results.append(check_corra_freshness(observation_date, pull_date, holidays=holidays))
    return results


def build_dq_results_for_pull(
    pull_date_str: str,
    single_series_observations: dict[str, list[dict[str, Any]]],
    corra_observations: list[dict[str, Any]],
    holidays: set[date] | None = None,
) -> list[dict[str, Any]]:
    """single_series_observations: {series_id: raw observation objects (not flattened)}."""
    results: list[dict[str, Any]] = []
    for series_id, observations in single_series_observations.items():
        results.extend(check_single_series_schema(series_id, observations))
    results.extend(check_corra_freshness_for_pull(pull_date_str, corra_observations, holidays=holidays))
    return results
