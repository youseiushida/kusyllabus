"""``kusyllabus agent-context`` — the machine-readable surface description."""

from __future__ import annotations

import typer

from kusyllabus.cli._common import emit_human, emit_json, get_options
from kusyllabus.cli._context import build_agent_context
from kusyllabus.cli._profile import ProfileStore

app = typer.Typer(help="Versioned machine-readable description of the CLI surface.")


@app.callback(invoke_without_command=True)
def show(ctx: typer.Context) -> None:
    """Emit the agent-context payload as JSON (always JSON, even without --json)."""
    if ctx.invoked_subcommand is not None:
        return
    from kusyllabus.cli import app as root_app

    payload = build_agent_context(root_app, profiles=ProfileStore().list_names())
    # agent-context is always JSON regardless of --json, per Rule 7.
    if get_options().json or True:
        emit_json(payload)
    else:
        emit_human(payload)
