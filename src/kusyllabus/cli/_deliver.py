"""Output delivery sinks (Rule 10).

Supported schemes:

* ``stdout`` — write to standard output (default).
* ``file:<path>`` — atomic write to a local file.
* ``webhook:<url>`` — HTTP POST with ``application/json`` body.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import httpx
import orjson

from kusyllabus.cli._common import emit_json
from kusyllabus.cli._errors import reject_enum

VALID_SCHEMES = ("stdout", "file:<path>", "webhook:<url>")


def deliver(payload: Any, target: str) -> dict[str, Any]:
    """Send ``payload`` to ``target`` and return a structured delivery summary."""
    if target == "stdout":
        emit_json(payload)
        return {"delivered_to": "stdout"}
    if target.startswith("file:"):
        path = Path(target[len("file:") :])
        return _deliver_file(payload, path)
    if target.startswith("webhook:"):
        url = target[len("webhook:") :]
        return _deliver_webhook(payload, url)
    reject_enum("--deliver", target, VALID_SCHEMES)


def _deliver_file(payload: Any, path: Path) -> dict[str, Any]:
    """Atomic write: temp file + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = orjson.dumps(payload, option=orjson.OPT_INDENT_2)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.write(b"\n")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        finally:
            raise
    return {"delivered_to": f"file:{path}", "bytes": len(encoded) + 1}


def _deliver_webhook(payload: Any, url: str) -> dict[str, Any]:
    body = orjson.dumps(payload)
    response = httpx.post(
        url,
        content=body,
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )
    return {
        "delivered_to": f"webhook:{url}",
        "status": response.status_code,
    }
