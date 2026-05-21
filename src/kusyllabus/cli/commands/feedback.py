"""``kusyllabus feedback`` — local-first friction reports (Rule 10)."""

from __future__ import annotations

from typing import Annotated

import typer

from kusyllabus.cli import _feedback
from kusyllabus.cli._common import emit_human, emit_json, get_options

app = typer.Typer(help="Report friction back to the maintainer.")


@app.command("add")
def add(
    text: Annotated[str, typer.Argument(help="Free-text feedback message.")],
) -> None:
    """Record one feedback entry (locally; POSTed upstream if configured)."""
    entry, upstream = _feedback.record(text)
    payload = {"entry": entry.model_dump(mode="json"), "upstream": upstream}
    if get_options().json:
        emit_json(payload)
        return
    msg = "feedback recorded locally"
    if "status" in upstream:
        msg += f" and sent upstream (status: {upstream['status']})"
    elif "error" in upstream:
        msg += f"; upstream POST failed: {upstream['error']}"
    emit_human(msg)


@app.command("list")
def list_() -> None:
    """List local feedback entries."""
    entries = _feedback.list_entries()
    if get_options().json:
        emit_json({"entries": [e.model_dump(mode="json") for e in entries]})
        return
    if not entries:
        emit_human("(no feedback entries)")
        return
    for e in entries:
        emit_human(f"{e.timestamp}  {e.text}")
