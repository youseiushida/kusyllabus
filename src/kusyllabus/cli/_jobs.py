"""Persistent JSONL job ledger for long-running CLI tasks.

Each line is a single JSON object describing one job. The append-only shape
keeps writes simple (no locking needed for the typical single-process CLI
flow) and the file is trivially inspectable with ``cat`` or ``jq``.

Rule 8 of the agent-native CLI principles: ``--wait`` should survive process
death. ``syllabus fetch-all`` registers a job here before issuing requests so
a subsequent invocation can find an in-flight job rather than starting a new
one. Resuming is best-effort — the actual retry/dedup logic lives in the
fetch-all command.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kusyllabus.cli._paths import jobs_path


class Job(BaseModel):
    """A single row in the JSONL ledger."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: str
    """Free-form job kind (e.g. ``syllabus.fetch-all``)."""

    status: str = "queued"
    """``queued`` | ``running`` | ``complete`` | ``failed`` | ``cancelled``."""

    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    progress: float | None = None
    """0.0–1.0 fraction complete, if applicable."""

    total: int | None = None
    completed: int | None = None
    failed: int | None = None

    params: dict[str, Any] = Field(default_factory=dict)
    output_path: str | None = None
    error: str | None = None


class JobsLedger:
    """Append-only JSONL store at :func:`jobs_path()`."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or jobs_path()

    # ----- IO -------------------------------------------------------------

    def append(self, job: Job) -> Job:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as f:
            f.write(json.dumps(job.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"))
            f.write(b"\n")
        return job

    def all_records(self) -> list[Job]:
        if not self.path.exists():
            return []
        records: dict[str, Job] = {}
        for raw_line in self.path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            job = Job.model_validate(obj)
            # Later writes win, so the latest status of a given job ID is used.
            records[job.id] = job
        return list(records.values())

    def get(self, job_id: str) -> Job | None:
        for job in self.all_records():
            if job.id == job_id:
                return job
        return None

    def prune(self, *, keep_running: bool = True) -> int:
        """Drop completed/failed jobs from the ledger. Returns count removed."""
        records = self.all_records()
        kept = [j for j in records if j.status in {"queued", "running"}] if keep_running else []
        removed = len(records) - len(kept)
        self.path.write_text(
            "\n".join(json.dumps(j.model_dump(mode="json"), ensure_ascii=False) for j in kept)
            + ("\n" if kept else ""),
            encoding="utf-8",
        )
        return removed
