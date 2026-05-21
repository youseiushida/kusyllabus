"""kusyllabus CLI.

Designed against the 10 agent-native CLI principles:

* Every data-returning command supports ``--json`` and writes data to stdout,
  diagnostics to stderr.
* Errors enumerate valid values (see :mod:`kusyllabus.cli._errors`).
* ``profile`` subcommand saves named bundles of search defaults
  (``--profile NAME`` everywhere, precedence: flag > env > profile > default).
* ``jobs`` subcommand exposes the JSONL ledger written by ``syllabus fetch-all``.
* ``agent-context`` emits versioned, machine-readable command schema.
* ``feedback`` collects friction reports locally with optional upstream POST.

Run ``kusyllabus --help`` for human help, ``kusyllabus agent-context`` for the
machine-readable surface description, and read ``docs/SKILL.md`` for the
long-form skill manifest.
"""

from __future__ import annotations

import typer

from kusyllabus.cli._common import GlobalOptions, configure_global_options
from kusyllabus.cli.commands import (
    agent,
    all_,
    feedback,
    jobs,
    master,
    profile,
    search,
    syllabus,
    titles,
)

app = typer.Typer(
    name="kusyllabus",
    help=(
        "Agent-friendly CLI for the Kyoto University open syllabus. "
        "Every data command supports --json. Run `kusyllabus agent-context` "
        "for the machine-readable surface description."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.callback()
def _root(
    json_: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON on stdout (otherwise human-readable).",
        envvar="KUSYLLABUS_JSON",
    ),
    profile_: str | None = typer.Option(
        None,
        "--profile",
        help="Use named profile defaults (see `kusyllabus profile list`).",
        envvar="KUSYLLABUS_PROFILE",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable ANSI colour even when stdout is a TTY.",
        envvar="NO_COLOR",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error diagnostics on stderr.",
    ),
) -> None:
    """Configure global options shared across every subcommand."""
    configure_global_options(
        GlobalOptions(
            json=json_,
            profile=profile_,
            no_color=no_color,
            quiet=quiet,
        )
    )


# Register subcommands as nouns. Verbs live on each module's typer.Typer.
app.add_typer(search.app, name="search", help="Search syllabi (`/search`).")
app.add_typer(syllabus.app, name="syllabus", help="Fetch single syllabi or bulk download.")
app.add_typer(all_.app, name="all", help="Walk the `/all` tree (every department).")
app.add_typer(titles.app, name="titles", help="Per-department academic-area dropdown values.")
app.add_typer(master.app, name="master", help="Master enums: departments, semesters, levels ...")
app.add_typer(profile.app, name="profile", help="Save and reuse search-condition profiles.")
app.add_typer(jobs.app, name="jobs", help="Inspect long-running background jobs.")
app.add_typer(feedback.app, name="feedback", help="Report friction back to the maintainer.")
app.add_typer(
    agent.app, name="agent-context", help="Versioned machine-readable surface description."
)


__all__ = ["app"]
