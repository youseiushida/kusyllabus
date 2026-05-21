"""``kusyllabus syllabus`` subcommands."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

import typer
from rich.panel import Panel

from kusyllabus import AsyncKuSyllabusClient, KuSyllabusClient, flatten_all_leaves
from kusyllabus.cli._common import emit_human, emit_json, error, get_options, info
from kusyllabus.cli._deliver import deliver
from kusyllabus.cli._jobs import Job, JobsLedger

app = typer.Typer(help="Get one syllabus or bulk-download many.")


@app.command("get")
def get_(
    lecture_no: Annotated[int, typer.Argument(help="lectureNo (integer).")],
    department_no: Annotated[
        int | None,
        typer.Option(
            "--department",
            "-d",
            help=(
                "Department code for /department_syllabus entries. Omit ONLY for "
                "the /la_syllabus pool (liberal-arts). `search list` returns "
                "department_no per row; pass it through here verbatim — lectureNo "
                "alone is ambiguous because the server reuses IDs across years "
                "between the two pools."
            ),
        ),
    ] = None,
    display_lang: Annotated[
        str | None, typer.Option("--lang", help="'ja' (default) or 'en'.")
    ] = None,
    deliver_to: Annotated[
        str | None,
        typer.Option("--deliver", help="stdout (default) | file:<path> | webhook:<url>."),
    ] = None,
) -> None:
    """Fetch a single syllabus. Returns ``null`` on 404 (with exit code 4).

    [bold]lectureNo alone is not unique.[/bold] Pass ``--department`` whenever
    you got the lectureNo from a `search list` row that carries
    ``department_no``; otherwise the server may return a recycled, years-old
    entry from the wrong pool.
    """
    with KuSyllabusClient() as ku:
        syllabus = ku.get_syllabus(
            lecture_no,
            department_no=department_no,
            display_lang=display_lang,
        )

    payload = syllabus.model_dump(mode="json") if syllabus else None
    if deliver_to:
        result = deliver(payload, deliver_to)
        if get_options().json:
            emit_json(result)
        else:
            emit_human(result)
        if syllabus is None:
            raise typer.Exit(code=4)
        return

    if syllabus is None:
        if get_options().json:
            emit_json(None)
        else:
            error(f"syllabus {lecture_no} not found", exit_code=4)
        raise typer.Exit(code=4)

    if get_options().json:
        emit_json(payload)
        return

    body = [
        f"[bold]{syllabus.title}[/bold]",
        f"  course #: {', '.join(syllabus.course_numbers) or '-'}",
        f"  teachers: {', '.join(t.name for t in syllabus.teachers)}",
        f"  language: {syllabus.language}    credits: {syllabus.credits}    style: {syllabus.class_style}",
        f"  when: {syllabus.year_semester}    where: {syllabus.days_and_periods}",
        "",
        "[bold]概要 / Overview[/bold]",
        (syllabus.overview_purpose or "").strip(),
        "",
        "[bold]到達目標 / Objectives[/bold]",
        (syllabus.objectives or "").strip(),
        "",
        "[bold]評価 / Evaluation[/bold]",
        (syllabus.evaluation or "").strip(),
    ]
    emit_human(Panel("\n".join(body), title=f"lectureNo={lecture_no}", expand=False))


@app.command("fetch-all")
def fetch_all(
    output: Annotated[
        str, typer.Option("--out", "-o", help="JSONL output file. Each line is one syllabus.")
    ],
    kind: Annotated[
        str, typer.Option("--kind", help="'open' (/la_syllabus only), 'department', or 'all'.")
    ] = "open",
    limit: Annotated[
        int | None, typer.Option("--limit", help="Stop after N records (handy for smoke-tests).")
    ] = None,
    max_at_once: Annotated[int, typer.Option("--concurrency", help="Max parallel requests.")] = 8,
    max_per_second: Annotated[
        float, typer.Option("--rps", help="Max requests per second (rate limit).")
    ] = 5.0,
    wait: Annotated[
        bool,
        typer.Option(
            "--wait/--no-wait", help="Block until done (default). --no-wait fires-and-forgets."
        ),
    ] = True,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite the output file if it exists.")
    ] = False,
    display_lang: Annotated[str | None, typer.Option("--lang")] = None,
) -> None:
    """Bulk-download syllabi to a local JSONL file.

    Writes one syllabus per line. Registers a row in the jobs ledger so a
    later ``kusyllabus jobs list`` shows in-flight/complete jobs. Per Rule 8,
    ``--wait`` (the default) collapses submit-poll-collect into one call.
    """
    valid_kinds = {"open", "department", "all"}
    if kind not in valid_kinds:
        error(f"--kind must be one of: {sorted(valid_kinds)} (got: {kind!r})", exit_code=2)

    from pathlib import Path

    out_path = Path(output)
    if out_path.exists() and not force:
        error(f"output file {out_path} already exists (pass --force to overwrite)", exit_code=2)

    ledger = JobsLedger()
    job = Job(
        kind="syllabus.fetch-all",
        status="running",
        params={
            "kind": kind,
            "limit": limit,
            "concurrency": max_at_once,
            "rps": max_per_second,
            "output": str(out_path),
            "display_lang": display_lang,
        },
        output_path=str(out_path),
    )
    ledger.append(job)

    if not wait:
        info(f"job {job.id} registered (use `kusyllabus jobs get {job.id}` to track)")
        if get_options().json:
            emit_json(job.model_dump(mode="json"))
        else:
            emit_human(f"queued job {job.id} (--no-wait); ledger: {ledger.path}")
        return

    async def _run() -> dict[str, int]:
        async with AsyncKuSyllabusClient() as ku:
            info("fetching /all tree to collect lecture IDs...")
            tree = await ku.get_all_tree(display_lang=display_lang)
            leaves = flatten_all_leaves(tree)
            if kind == "open":
                leaves = [n for n in leaves if n.kind == "open_syllabus"]
            elif kind == "department":
                leaves = [n for n in leaves if n.kind == "department_syllabus"]
            else:
                leaves = [n for n in leaves if n.lecture_no is not None]
            if limit:
                leaves = leaves[:limit]

            targets: list[tuple[int, int | None]] = [
                (n.lecture_no, n.department_no if n.kind == "department_syllabus" else None)
                for n in leaves
                if n.lecture_no is not None
            ]
            total_n = len(targets)

            info(f"fetching {total_n} syllabi (concurrency={max_at_once}, rps={max_per_second})")
            done = 0
            failed = 0
            with out_path.open("wb") as f:
                results = await ku.fetch_many_syllabi(
                    targets,
                    max_at_once=max_at_once,
                    max_per_second=max_per_second,
                    display_lang=display_lang,
                )
                for syl in results:
                    if syl is None:
                        failed += 1
                        continue
                    done += 1
                    f.write(
                        json.dumps(syl.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")
                    )
                    f.write(b"\n")

            return {"total": total_n, "done": done, "failed": failed}

    stats = asyncio.run(_run())
    job.status = "complete"
    job.total = stats["total"]
    job.completed = stats["done"]
    job.failed = stats["failed"]
    job.progress = 1.0 if stats["total"] else None
    ledger.append(job)

    payload = {"job_id": job.id, **stats, "output": str(out_path)}
    if get_options().json:
        emit_json(payload)
    else:
        emit_human(
            f"job {job.id} complete: wrote {stats['done']}/{stats['total']} "
            f"syllabi to {out_path} ({stats['failed']} failed)"
        )
