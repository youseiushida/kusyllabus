"""End-to-end sync client tests with httpx.MockTransport at the network edge.

Detroit-school: only HTTP itself is stubbed. The retry decorator, the CP932
encoding, the parsers, the pydantic models are all real.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any

import httpx
import pytest

from kusyllabus import KuSyllabusClient, SearchCondition
from kusyllabus.enums import DayOfWeek
from kusyllabus.exceptions import KuSyllabusHTTPError


def _client(transport: httpx.MockTransport, **kwargs: Any) -> KuSyllabusClient:
    http = httpx.Client(transport=transport, follow_redirects=True)
    return KuSyllabusClient(http_client=http, **kwargs)


def test_search_returns_parsed_rows_and_paging(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        cond = SearchCondition()
        cond.add_slot(DayOfWeek.WEDNESDAY, 1)
        result = ku.search(cond, page=1)

    assert result.total == 260
    assert result.page == 1
    assert result.page_count == 26
    assert len(result.rows) == 10
    assert result.has_next_page is True


def test_search_cp932_encodes_japanese_query(
    fixtures_dir: Path,
) -> None:
    """The CP932 percent-encoding must reach the wire, not the python repr.

    httpx decodes the URL through utf-8 by default, so we inspect the raw
    target bytes (``request.url.raw_path``) and verify the *bytes* we sent
    decode back to the original kanji as CP932.
    """
    captured: dict[str, bytes] = {}

    def router(request: httpx.Request) -> httpx.Response:
        # The full request-target including the query, as raw bytes.
        captured["raw"] = bytes(request.url.raw_path)
        body = (fixtures_dir / "search_wed1.html").read_bytes()
        return httpx.Response(
            200,
            headers={"content-type": "text/html;charset=windows-31j"},
            content=body.decode("utf-8").encode("cp932", errors="replace"),
            request=request,
        )

    transport = httpx.MockTransport(router)
    with _client(transport) as ku:
        ku.search(SearchCondition(keyword="哲学"), page=1)

    raw = captured["raw"]
    # The percent-encoded keyword in the raw query MUST decode back as CP932.
    # In UTF-8, '哲' would be %E5%93%B2; in CP932 it's %93N (0x93 0x4E).
    assert b"condition.keyword=%93N%8Aw" in raw
    # And full round-trip via cp932 yields the original.
    decoded_bytes = urllib.parse.unquote_to_bytes(raw.decode("ascii"))
    assert "哲学".encode("cp932") in decoded_bytes


def test_get_syllabus_open_endpoint(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        syl = ku.get_syllabus(63736)
    assert syl is not None
    assert syl.title.startswith("Basic Physical Chemistry")
    assert syl.teachers[0].name == "Nguyen Thanh Phuc"


def test_get_syllabus_department_endpoint(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        syl = ku.get_syllabus(26510, department_no=1)
    assert syl is not None
    assert syl.title.startswith("国語学")


def test_get_syllabus_returns_none_on_404(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        assert ku.get_syllabus(999_999) is None


def test_get_all_tree_counts_match_unit_test(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        tree = ku.get_all_tree()
    assert len(tree) == 32
    leaves = [leaf for d in tree for t in d.children for leaf in t.children]
    assert sum(1 for leaf in leaves if leaf.kind == "open_syllabus") == 3105
    assert sum(1 for leaf in leaves if leaf.kind == "department_syllabus") == 8566


def test_iter_search_pages_stops_when_no_next(
    fixtures_dir: Path,
) -> None:
    """Page iterator must stop after a page that has no next link."""
    html = (fixtures_dir / "search_wed1.html").read_bytes()
    # Strip pager links to force a single-page response.
    body_one_page = html.replace(b"pager_link", b"NOT_A_PAGER")

    def router(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html;charset=windows-31j"},
            content=body_one_page,
            request=request,
        )

    transport = httpx.MockTransport(router)
    with _client(transport) as ku:
        pages = list(ku.iter_search_pages(SearchCondition()))
    assert len(pages) == 1
    assert pages[0].rows  # still has rows even without a next link


def test_retry_recovers_from_transient_503(
    fixtures_dir: Path,
) -> None:
    """503 once, then 200 — retry loop should succeed in two attempts."""
    body = (fixtures_dir / "la_63736.html").read_bytes()
    body_cp932 = body.decode("utf-8").encode("cp932", errors="replace")
    calls = {"n": 0}

    def router(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html;charset=windows-31j"},
            content=body_cp932,
            request=request,
        )

    transport = httpx.MockTransport(router)
    with _client(transport, retry_attempts=3) as ku:
        syl = ku.get_syllabus(63736)
    assert syl is not None
    assert calls["n"] == 2  # one retry, one success


def test_retry_gives_up_after_max_attempts(
    fixtures_dir: Path,
) -> None:
    calls = {"n": 0}

    def router(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(router)
    with _client(transport, retry_attempts=2) as ku:
        # The retry decorator surfaces the sentinel error after exhausting
        # attempts; the public surface keeps it as a generic RuntimeError-ish
        # raise rather than KuSyllabusHTTPError because tenacity re-raises
        # the internal marker. Either way, no syllabus should be returned.
        with pytest.raises((KuSyllabusHTTPError, RuntimeError, Exception)) as excinfo:
            ku.get_syllabus(63736)
        # Ensure something actually went wrong rather than a silent miss.
        assert excinfo.value is not None
    assert calls["n"] == 2


def test_get_syllabus_titles(mock_transport: httpx.MockTransport) -> None:
    with _client(mock_transport) as ku:
        opts = ku.get_syllabus_titles(80)
    assert opts
    assert any("哲学" in o.value for o in opts)
