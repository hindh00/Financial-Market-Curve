"""Data-quality checks that aren't naturally SQL-shaped and so live in Python
rather than as dbt tests (see dbt/tests/ for the SQL-shaped ones: curve
integrity, holiday-aware completeness, referential integrity).

Covered here:
  - freshness / lookahead risk (CORRA's next-morning publish lag)
  - >4 std-dev jump detection
  - revision diffing between two pulls of the same observation_date
  - API schema drift (fields appearing/disappearing between pulls)

Each check returns a list of result dicts shaped like a row of
gold_dq_results, so the same function can be unit-tested here and also
called from a small script that lands its output into the Volume for dbt
to pick up (see docs/architecture.md).
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Any

# CORRA is published the business day AFTER the trades it covers (MTRS
# submission deadline 22:00 ET, CORRA published 9:00-11:00 ET the next
# business day). Treating a CORRA value as available on its own
# observation_date is a lookahead error.
CORRA_PUBLISH_LAG_BUSINESS_DAYS = 1


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def check_corra_freshness(observation_date: date, pull_date: date, holidays: set[date] | None = None) -> dict[str, Any]:
    """Flag a lookahead error if CORRA for observation_date was used as of
    a pull_date that's not at least one business day later."""
    holidays = holidays or set()
    expected_available_date = observation_date
    days_advanced = 0
    cursor = observation_date
    while days_advanced < CORRA_PUBLISH_LAG_BUSINESS_DAYS:
        cursor += timedelta(days=1)
        if not _is_weekend(cursor) and cursor not in holidays:
            days_advanced += 1
    expected_available_date = cursor

    passed = pull_date >= expected_available_date
    return {
        "check_name": "corra_freshness",
        "observation_date": observation_date.isoformat(),
        "pull_date": pull_date.isoformat(),
        "status": "pass" if passed else "fail",
        "severity": "high" if not passed else "info",
        "details": f"CORRA for {observation_date} not available until {expected_available_date}",
    }


def check_jump(series_id: str, dated_values: list[tuple[date, float]], threshold_std: float = 4.0) -> list[dict[str, Any]]:
    """Flag daily changes that are statistical outliers relative to the
    series' typical daily change, using a robust (median/MAD-based) z-score
    rather than mean/stdev. A classical mean+stdev z-score computed over the
    same window the outlier is drawn from gets inflated by the outlier
    itself, which can mask the very jump it's meant to catch; the median
    absolute deviation doesn't have that failure mode. `threshold_std` is
    expressed in "standard-deviation-equivalent" units (robust z-score),
    matching the spec's ">4 standard deviations" framing.

    Caller is responsible for excluding (or the gold layer for
    re-including as "explained") benchmark-switch days — this function has
    no notion of switches, it just flags jumps.
    """
    if len(dated_values) < 3:
        return []

    sorted_values = sorted(dated_values, key=lambda dv: dv[0])
    changes = [
        (sorted_values[i][0], sorted_values[i][1] - sorted_values[i - 1][1])
        for i in range(1, len(sorted_values))
    ]
    deltas = [c[1] for c in changes]
    median = statistics.median(deltas)
    mad = statistics.median([abs(d - median) for d in deltas])
    # 0.6745 scales MAD to be comparable to a standard deviation under normality.
    robust_scale = mad / 0.6745 if mad > 0 else 0.0

    results = []
    for change_date, delta in changes:
        if robust_scale == 0:
            continue
        z = abs(delta - median) / robust_scale
        if z > threshold_std:
            results.append({
                "check_name": "jump_check",
                "series_id": series_id,
                "observation_date": change_date.isoformat(),
                "status": "fail",
                "severity": "medium",
                "details": f"Change {delta:+.4f} is {z:.1f} robust std devs from the typical change {median:+.4f}",
            })
    return results


def diff_revision(series_id: str, observation_date: date, prior_pull_value: float | None, new_pull_value: float | None) -> dict[str, Any] | None:
    """Return a revision-log row if the value for the same observation_date
    changed between two pulls, else None."""
    if prior_pull_value is None or new_pull_value is None:
        return None
    if prior_pull_value == new_pull_value:
        return None
    return {
        "check_name": "revision_detected",
        "series_id": series_id,
        "observation_date": observation_date.isoformat(),
        "status": "info",
        "severity": "info",
        "details": f"Value revised from {prior_pull_value} to {new_pull_value}",
        "old_value": prior_pull_value,
        "new_value": new_pull_value,
    }


def check_schema_drift(series_id: str, prior_fields: set[str], new_fields: set[str]) -> dict[str, Any] | None:
    """Flag when the API response's field set changes between pulls."""
    added = new_fields - prior_fields
    removed = prior_fields - new_fields
    if not added and not removed:
        return None
    return {
        "check_name": "schema_drift",
        "series_id": series_id,
        "status": "fail",
        "severity": "high",
        "details": f"Fields added: {sorted(added)}; fields removed: {sorted(removed)}",
    }


def check_holiday_aware_gap(expected_dates: set[date], observed_dates: set[date], holidays: set[date]) -> list[dict[str, Any]]:
    """A missing business day is an error; a missing holiday or weekend is expected."""
    missing = expected_dates - observed_dates
    results = []
    for d in sorted(missing):
        if _is_weekend(d) or d in holidays:
            continue
        results.append({
            "check_name": "holiday_aware_completeness",
            "observation_date": d.isoformat(),
            "status": "fail",
            "severity": "high",
            "details": f"{d.isoformat()} is a business day with no observation",
        })
    return results
