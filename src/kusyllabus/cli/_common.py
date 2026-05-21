"""Shared CLI helpers — global options, JSON/human output, error formatting."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

import orjson
import typer
from pydantic import BaseModel
from rich.console import Console

# Windows consoles default to cp932, which can't encode characters used by
# rich (box-drawing) or by Japanese syllabus content. Reconfigure once at
# import time so every subsequent print works regardless of platform.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


@dataclass
class GlobalOptions:
    """Resolved global flags. Populated by the root callback."""

    json: bool = False
    profile: str | None = None
    no_color: bool = False
    quiet: bool = False
    consoles: dict[str, Console] = field(default_factory=dict)


_GLOBAL = GlobalOptions()


def configure_global_options(options: GlobalOptions) -> None:
    """Replace the global option state and rebuild the rich consoles."""
    global _GLOBAL
    options.consoles = {
        "out": Console(
            file=sys.stdout,
            force_terminal=False,
            no_color=options.no_color,
            highlight=False,
        ),
        "err": Console(
            file=sys.stderr,
            force_terminal=False,
            no_color=options.no_color,
            highlight=False,
            stderr=True,
        ),
    }
    _GLOBAL = options


def get_options() -> GlobalOptions:
    return _GLOBAL


def stdout() -> Console:
    return _GLOBAL.consoles.get("out") or Console(file=sys.stdout)


def stderr() -> Console:
    return _GLOBAL.consoles.get("err") or Console(file=sys.stderr, stderr=True)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def emit_json(payload: Any) -> None:
    """Write ``payload`` to stdout as compact JSON ending in a newline.

    Handles pydantic models via ``model_dump(mode='json')`` automatically.
    """
    encoded = _json_dumps(payload)
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.flush()


def emit_human(renderable: Any) -> None:
    """Render an arbitrary Rich renderable / string to stdout."""
    stdout().print(renderable)


def info(message: str) -> None:
    """Non-error diagnostic; goes to stderr (respects --quiet)."""
    if _GLOBAL.quiet:
        return
    stderr().print(f"[dim]{message}[/dim]")


def warn(message: str) -> None:
    stderr().print(f"[yellow]warning:[/yellow] {message}")


def error(message: str, exit_code: int = 1) -> None:
    """Print a structured error to stderr and exit with ``exit_code``."""
    stderr().print(f"[red]error:[/red] {message}")
    raise typer.Exit(code=exit_code)


def _json_dumps(payload: Any) -> bytes:
    return orjson.dumps(
        payload,
        default=_json_default,
        option=orjson.OPT_NON_STR_KEYS,
    )


def _json_default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__iter__"):
        return list(obj)
    raise TypeError(f"cannot serialize {type(obj).__name__} to JSON")
