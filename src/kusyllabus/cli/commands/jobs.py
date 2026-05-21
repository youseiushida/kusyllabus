"""``kusyllabus jobs`` — inspect the JSONL job ledger."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kusyllabus.cli._common import emit_human, emit_json, error, get_options
from kusyllabus.cli._jobs import JobsLedger

app = typer.Typer(help="Inspect background jobs (e.g. `syllabus fetch-all`).")


@app.command("list")
def list_(
    status: Annotated[
        str | None,
        typer.Option(
            "--status", help="Filter by status: queued/running/complete/failed/cancelled."
        ),
    ] = None,
) -> None:
    """List jobs from the ledger."""
    ledger = JobsLedger()
    rows = ledger.all_records()
    if status:
        rows = [j for j in rows if j.status == status]
    if get_options().json:
        emit_json({"path": str(ledger.path), "jobs": [j.model_dump(mode="json") for j in rows]})
        return
    if not rows:
        emit_human("(no jobs)")
        return
    t = Table()
    for col in ("id", "kind", "status", "progress", "started", "output"):
        t.add_column(col)
    for j in rows:
        progress = f"{j.completed or 0}/{j.total or '?'}"
        t.add_row(j.id, j.kind, j.status, progress, j.started_at, j.output_path or "-")
    emit_human(t)


@app.command("get")
def get_(
    job_id: Annotated[str, typer.Argument()],
) -> None:
    """Show one job."""
    ledger = JobsLedger()
    job = ledger.get(job_id)
    if job is None:
        error(f"job {job_id!r} not found", exit_code=4)
    if get_options().json:
        emit_json(job.model_dump(mode="json"))
    else:
        emit_human(job.model_dump(mode="json"))


@app.command("prune")
def prune(
    force: Annotated[
        bool, typer.Option("--force", help="Required to actually delete completed/failed rows.")
    ] = False,
) -> None:
    """Remove completed/failed rows from the ledger."""
    if not force:
        error("pass --force to confirm pruning", exit_code=2)
    ledger = JobsLedger()
    removed = ledger.prune()
    if get_options().json:
        emit_json({"removed": removed})
    else:
        emit_human(f"removed {removed} job record(s)")
