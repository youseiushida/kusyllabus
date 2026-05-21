"""Internal parser helpers."""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser, Node

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_WS_RE = re.compile(r"[ \t　]+")
_LECTURE_NO_RE = re.compile(r"lectureNo=(\d+)")


def lines_from(node: Node) -> list[str]:
    """Return text lines from a node, treating ``<br>`` as line break.

    ``selectolax``'s ``text()`` discards the line-break semantics of ``<br>``,
    so we re-parse with ``<br>`` replaced by ``\n`` and then split.
    """
    html = node.html or ""
    inner = _BR_RE.sub("\n", html)
    text = HTMLParser(inner).text(deep=True)
    return [_WS_RE.sub(" ", line).strip() for line in text.split("\n") if line and line.strip()]


def text_of(node: Node | None) -> str:
    """Whitespace-collapsed text of a node, or empty string if None."""
    if node is None:
        return ""
    return _WS_RE.sub(" ", node.text(deep=True)).strip()


def extract_lecture_no(href: str | None) -> int | None:
    if not href:
        return None
    m = _LECTURE_NO_RE.search(href)
    return int(m.group(1)) if m else None
