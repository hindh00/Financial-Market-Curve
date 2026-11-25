"""Push landed snapshot JSON into the Databricks Unity Catalog Volume via an
inbound Files-API call — not subject to Free Edition's outbound-internet
allowlist, which is why the Valet pull itself happens in GitHub Actions
rather than a Databricks notebook/job.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests


class DatabricksUploadError(RuntimeError):
    pass


@dataclass
class DatabricksConfig:
    host: str  # bare hostname, e.g. <workspace>.cloud.databricks.com — no scheme
    token: str
    volume_path: str  # e.g. /Volumes/financial_market_curve/bronze/raw_valet

    @classmethod
    def from_env(cls) -> "DatabricksConfig":
        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")
        volume_path = os.environ.get("DATABRICKS_VOLUME_PATH")
        missing = [name for name, val in [
            ("DATABRICKS_HOST", host), ("DATABRICKS_TOKEN", token), ("DATABRICKS_VOLUME_PATH", volume_path),
        ] if not val]
        if missing:
            raise DatabricksUploadError(f"Missing required env vars: {', '.join(missing)}")
        # dbt-databricks' profiles.yml wants a bare hostname; strip any scheme
        # here since upload_json below is the one place that rebuilds a full URL.
        host = host.rstrip("/")
        for scheme in ("https://", "http://"):
            if host.startswith(scheme):
                host = host[len(scheme):]
        return cls(host=host, token=token, volume_path=volume_path.rstrip("/"))


def upload_json(config: DatabricksConfig, relative_path: str, envelope: dict) -> None:
    """PUT the envelope to {volume_path}/{relative_path}; overwrite is safe
    since relative_path is keyed on pull_date, so only today's file is touched."""
    full_path = f"{config.volume_path}/{relative_path}"
    url = f"https://{config.host}/api/2.0/fs/files{full_path}"
    body = json.dumps(envelope).encode("utf-8")

    resp = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/octet-stream",
        },
        params={"overwrite": "true"},
        data=body,
        timeout=30,
    )
    if resp.status_code not in (200, 204):
        raise DatabricksUploadError(
            f"Upload to {full_path} failed: HTTP {resp.status_code}: {resp.text[:300]}"
        )
