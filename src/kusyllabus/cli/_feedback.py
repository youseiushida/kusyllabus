"""Feedback collection (Rule 10).

Local-first: every entry lands in ``state_dir/feedback.jsonl``. When the
``KUSYLLABUS_FEEDBACK_ENDPOINT`` env var is set, the entry is also POSTed
upstream in JSON.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from kusyllabus import __name__ as _pkg_name
from kusyllabus.cli._paths import feedback_path

ENDPOINT_ENV = "KUSYLLABUS_FEEDBACK_ENDPOINT"


class FeedbackEntry(BaseModel):
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    cli_version: str | None = None
    platform: str = Field(default_factory=lambda: platform.platform())
    metadata: dict[str, Any] = Field(default_factory=dict)


def record(
    text: str, *, metadata: dict[str, Any] | None = None
) -> tuple[FeedbackEntry, dict[str, Any]]:
    """Append a feedback entry locally and (if configured) POST upstream.

    Returns ``(entry, upstream_result)``. ``upstream_result`` is empty when
    no endpoint is configured; otherwise it contains ``{"status": int}`` or
    ``{"error": str}``.
    """
    entry = FeedbackEntry(text=text.strip(), metadata=metadata or {}, cli_version=_pkg_version())
    _append(feedback_path(), entry)
    upstream = _post_upstream(entry)
    return entry, upstream


def list_entries() -> list[FeedbackEntry]:
    path = feedback_path()
    if not path.exists():
        return []
    out: list[FeedbackEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(FeedbackEntry.model_validate(json.loads(line)))
        except (ValueError, json.JSONDecodeError):
            continue
    return out


def _append(path: Path, entry: FeedbackEntry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as f:
        f.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"))
        f.write(b"\n")


def _post_upstream(entry: FeedbackEntry) -> dict[str, Any]:
    endpoint = os.environ.get(ENDPOINT_ENV)
    if not endpoint:
        return {}
    try:
        response = httpx.post(
            endpoint,
            json=entry.model_dump(mode="json"),
            timeout=10.0,
        )
        return {"status": response.status_code}
    except httpx.HTTPError as exc:
        return {"error": str(exc)}


def _pkg_version() -> str | None:
    try:
        from importlib.metadata import version

        return version(_pkg_name.split(".")[0])
    except Exception:
        return None


__all__ = ["ENDPOINT_ENV", "FeedbackEntry", "list_entries", "record"]
