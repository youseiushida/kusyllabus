"""Shared pytest fixtures.

Detroit/Classical-school TDD: stub at the *network* boundary only. Real
parsers, real pydantic models, real client logic, real CLI runner. We feed
recorded HTML through ``httpx.MockTransport`` so the rest of the system runs
unmodified.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Return a fixture file's text (already decoded into ``str``)."""
    path = FIXTURES / name
    return path.read_text(encoding="utf-8")


def load_fixture_bytes(name: str) -> bytes:
    """Return the fixture body re-encoded as CP932, matching the live server."""
    return load_fixture(name).encode("cp932", errors="replace")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def fixture_text() -> Callable[[str], str]:
    return load_fixture


@pytest.fixture
def isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect platformdirs-driven paths into ``tmp_path``.

    Profile / jobs / feedback all sit under platformdirs by default; redirect
    so individual tests don't pollute the developer's real config.
    """
    cfg = tmp_path / "config"
    state = tmp_path / "state"
    cache = tmp_path / "cache"
    cfg.mkdir()
    state.mkdir()
    cache.mkdir()

    import kusyllabus.cli._paths as paths_mod

    monkeypatch.setattr(paths_mod, "config_dir", lambda: cfg)
    monkeypatch.setattr(paths_mod, "state_dir", lambda: state)
    monkeypatch.setattr(paths_mod, "cache_dir", lambda: cache)
    monkeypatch.setattr(paths_mod, "profiles_path", lambda: cfg / "profiles.json")
    monkeypatch.setattr(paths_mod, "jobs_path", lambda: state / "jobs.jsonl")
    monkeypatch.setattr(paths_mod, "feedback_path", lambda: state / "feedback.jsonl")
    return tmp_path


# ---------------------------------------------------------------------------
# Reusable MockTransport router covering every endpoint kusyllabus knows.
# ---------------------------------------------------------------------------


def _route(request: httpx.Request) -> httpx.Response:
    """Map a request to a recorded fixture response (CP932 bytes)."""
    path = request.url.path
    query = dict(request.url.params)
    headers = {"content-type": "text/html;charset=windows-31j"}

    def respond(name: str, status: int = 200) -> httpx.Response:
        return httpx.Response(
            status, headers=headers, content=load_fixture_bytes(name), request=request
        )

    if path.endswith("/open_syllabus/top"):
        if query.get("display_lang") == "en":
            return respond("top_en.html")
        return respond("top_ja.html")
    if path.endswith("/open_syllabus/all"):
        return respond("all.html")
    if path.endswith("/open_syllabus/open_syllabus_titles"):
        dept = query.get("departmentNo", "")
        if dept == "80":
            return respond("titles_dept80.html")
        if dept == "1":
            return respond("titles_dept1.html")
        return httpx.Response(
            200,
            headers=headers,
            content=b'<option value="" class="form_disable">----</option>',
            request=request,
        )
    if path.endswith("/open_syllabus/search"):
        if query.get("display_lang") == "en":
            return respond("search_en_p1.html")
        return respond("search_wed1.html")
    if path.endswith("/open_syllabus/la_syllabus"):
        lecture_no = query.get("lectureNo", "")
        # ``999999`` is the conventional "missing" probe in the tests.
        if lecture_no == "999999":
            return httpx.Response(404, request=request)
        # Map known IDs to their specific fixtures; fall back to la_63736 so
        # `fetch-all` etc. against the whole /all tree still produces useful
        # bodies without needing a fixture per lectureNo.
        mapping = {
            "63736": "la_63736_en.html" if query.get("display_lang") == "en" else "la_63736.html",
            "62409": "la_62409.html",
            "61585": "la_61585.html",
        }
        fixture = mapping.get(lecture_no, "la_63736.html")
        return respond(fixture)
    if path.endswith("/open_syllabus/department_syllabus"):
        return respond("department_syllabus_sample.html")
    return httpx.Response(404, request=request)


@pytest.fixture
def mock_transport() -> httpx.MockTransport:
    return httpx.MockTransport(_route)


@pytest.fixture
def httpx_client(mock_transport: httpx.MockTransport) -> Iterator[httpx.Client]:
    """A sync httpx client wired to the fixture router."""
    with httpx.Client(transport=mock_transport, base_url="https://example.invalid/") as c:
        yield c


@pytest.fixture
def async_httpx_client(mock_transport: httpx.MockTransport) -> Any:
    return httpx.AsyncClient(transport=mock_transport, base_url="https://example.invalid/")
