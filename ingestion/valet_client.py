"""Thin HTTP client for the Bank of Canada Valet API.

Reference: https://www.bankofcanada.ca/valet/docs
No business logic lives here — just typed, retrying HTTP calls that raise on
failure rather than returning partial/garbage data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from ingestion.config import VALET_BASE_URL


class ValetAPIError(RuntimeError):
    """Raised when the Valet API returns a non-200 response or bad JSON."""


@dataclass
class ValetResponse:
    url: str
    http_status: int
    payload: dict[str, Any]


class ValetClient:
    def __init__(self, base_url: str = VALET_BASE_URL, timeout_s: float = 15.0, max_retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def _get(self, path: str, params: dict[str, Any] | None = None) -> ValetResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout_s)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2**attempt, 10))
                continue

            if resp.status_code != 200:
                last_error = ValetAPIError(f"{url} returned HTTP {resp.status_code}: {resp.text[:300]}")
                if resp.status_code >= 500:
                    time.sleep(min(2**attempt, 10))
                    continue
                raise last_error

            try:
                payload = resp.json()
            except ValueError as exc:
                raise ValetAPIError(f"{url} returned non-JSON body: {resp.text[:300]}") from exc

            return ValetResponse(url=url, http_status=resp.status_code, payload=payload)

        raise ValetAPIError(f"Failed to fetch {url} after {self.max_retries} attempts: {last_error}")

    def get_series_observations(
        self,
        series_name: str,
        recent: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ValetResponse:
        """GET /observations/{series_name}/json.

        Either pass `recent` (the daily pull's rolling window) or
        `start_date`/`end_date` (a one-off historical range, used by
        ingestion/backfill.py) — not both.
        """
        params = self._observation_params(recent, start_date, end_date)
        return self._get(f"observations/{series_name}/json", params=params)

    def get_group_observations(
        self,
        group_name: str,
        recent: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ValetResponse:
        """GET /observations/group/{group_name}/json — a group (e.g. CORRA's AVG.INTWO)."""
        params = self._observation_params(recent, start_date, end_date)
        return self._get(f"observations/group/{group_name}/json", params=params)

    @staticmethod
    def _observation_params(
        recent: int | None, start_date: str | None, end_date: str | None
    ) -> dict[str, Any] | None:
        if recent and (start_date or end_date):
            raise ValueError("Pass either `recent` or `start_date`/`end_date`, not both")
        if recent:
            return {"recent": recent}
        if start_date or end_date:
            params: dict[str, Any] = {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return params
        return None

    def list_series(self) -> ValetResponse:
        """GET /lists/series/json — every series Valet publishes, with descriptions."""
        return self._get("lists/series/json")

    def list_groups(self) -> ValetResponse:
        """GET /lists/groups/json — every group Valet publishes."""
        return self._get("lists/groups/json")
