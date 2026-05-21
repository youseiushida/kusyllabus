"""Structured CLI errors — always enumerate valid values when rejecting input.

Rule 3 of the agent-native CLI principles: errors must teach. When the
failure is "you passed an invalid value", the message has to include the
valid set so the agent can self-correct in one retry.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, NoReturn

from kusyllabus.cli._common import error


def reject_enum(flag: str, value: Any, valid: Iterable[Any]) -> NoReturn:
    """Refuse a flag value, naming the valid set inline."""
    valid_list = ", ".join(str(v) for v in valid)
    error(
        f"{flag} must be one of: {valid_list} (got: {value!r})",
        exit_code=2,
    )


def reject_missing(flag: str, hint: str = "") -> NoReturn:
    suffix = f" — {hint}" if hint else ""
    error(f"{flag} is required{suffix}", exit_code=2)


def reject_pagination(page: int) -> NoReturn:
    error(
        f"--page must be >= 1 (upstream returns HTTP 500 for page<=0). got: {page}",
        exit_code=2,
    )
