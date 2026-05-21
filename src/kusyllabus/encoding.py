"""CP932 (windows-31j) helpers.

Open syllabus accepts and returns text exclusively in CP932. URL parameters
containing Japanese must be percent-encoded as CP932, and response bodies must
be decoded as CP932.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable, Mapping

CP932 = "cp932"


def quote_value(value: str) -> str:
    """Percent-encode a single query-string value using CP932."""
    return urllib.parse.quote(value, encoding=CP932, safe="")


def build_query(params: Iterable[tuple[str, str]] | Mapping[str, str]) -> str:
    """Build a query string with CP932-encoded values.

    Keys are encoded as ASCII (preserving `[` and `]` in `weekSchedule[31]`),
    values as CP932. Empty values are preserved (the server distinguishes
    `condition.foo=` from missing keys for some fields).
    """
    if isinstance(params, Mapping):
        items = list(params.items())
    else:
        items = list(params)
    parts = []
    for k, v in items:
        k_enc = urllib.parse.quote(str(k), encoding="ascii", safe="[].")
        v_enc = quote_value("" if v is None else str(v))
        parts.append(f"{k_enc}={v_enc}")
    return "&".join(parts)


def decode_response(raw: bytes) -> str:
    """Decode bytes from an open-syllabus response. Replaces undecodable bytes."""
    return raw.decode(CP932, errors="replace")
