"""Push landed snapshot JSON into the Databricks Unity Catalog Volume.

This is an INBOUND call (GitHub Actions -> Databricks Files API), which is
not subject to Databricks Free Edition's outbound-internet allowlist —
that restriction only applies to calls made FROM Databricks compute TO the
public internet (e.g. a notebook calling bankofcanada.ca). That's exactly
why the Valet pull happens here in GitHub Actions rather than in a
Databricks notebook/job.
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
    host: str  # e.g. https://<workspace>.cloud.databricks.com
    token: str
    volume_path: str  # e.g. /Volumes/fmc/bronze/raw_valet

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
        return cls(host=host.rstrip("/"), token=token, volume_path=volume_path.rstrip("/"))


def upload_json(config: DatabricksConfig, relative_path: str, envelope: dict) -> None:
    """PUT the envelope JSON to {volume_path}/{relative_path} via the Files API.

    Uses the Databricks Files REST API (PUT /api/2.0/fs/files{path}), which
    overwrites in place — safe here because relative_path is keyed on
    pull_date, so only today's file is ever touched.
    """
    full_path = f"{config.volume_path}/{relative_path}"
    url = f"{config.host}/api/2.0/fs/files{full_path}"
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
