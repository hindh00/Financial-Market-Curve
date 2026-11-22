"""Resolve the current Real Return Bond benchmark series id dynamically.

Why this can't be hardcoded: the government ceased issuing new RRBs in 2022,
so the benchmark the Bank designates as "current" (currently the 2050-12-01,
0.50% issue) is a fixed, aging bond with no replacement. The Bank could in
principle redesignate a different RRB as the benchmark at any time, and this
project's breakeven-inflation feature must stay correct if that happens
rather than silently computing against a stale id.

Strategy: call /lists/series/json and match on description text. If the
match is ambiguous (zero or multiple candidates), fail loudly — a silent
wrong pick would corrupt every downstream breakeven-inflation number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.config import RRB_DESCRIPTION_PATTERN
from ingestion.valet_client import ValetClient


class RRBResolutionError(RuntimeError):
    """Raised when zero or multiple RRB benchmark candidates are found."""


@dataclass
class RRBResolution:
    series_id: str
    description: str
    candidates_considered: int


def resolve_current_rrb_series(client: ValetClient) -> RRBResolution:
    response = client.list_series()
    series_map = response.payload.get("series", {})
    if not series_map:
        raise RRBResolutionError("lists/series/json returned no 'series' key — API shape may have changed")

    pattern = re.compile(RRB_DESCRIPTION_PATTERN, re.IGNORECASE)
    candidates: list[tuple[str, str]] = []
    for series_id, meta in series_map.items():
        text = " ".join(
            str(meta.get(field, "")) for field in ("label", "description") if isinstance(meta, dict)
        )
        if pattern.search(text):
            candidates.append((series_id, text.strip()))

    if len(candidates) == 0:
        raise RRBResolutionError(
            "No series matched the RRB description pattern — the Bank may have changed "
            "its naming convention. Update RRB_DESCRIPTION_PATTERN in ingestion/config.py."
        )
    if len(candidates) > 1:
        ids = ", ".join(c[0] for c in candidates)
        raise RRBResolutionError(
            f"Found {len(candidates)} RRB candidates ({ids}) — cannot pick one automatically. "
            "Narrow RRB_DESCRIPTION_PATTERN or add an explicit disambiguation rule."
        )

    series_id, description = candidates[0]
    return RRBResolution(series_id=series_id, description=description, candidates_considered=len(series_map))
