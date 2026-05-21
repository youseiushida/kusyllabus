"""End-to-end CLI tests using Typer's CliRunner + MockTransport.

We monkeypatch the two httpx clients in ``kusyllabus.client`` so every CLI
command reaches the fixture router instead of the live server.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from kusyllabus.cli import app


@pytest.fixture(autouse=True)
def _isolate_state(isolated_state_dir: Path) -> Iterator[Path]:
    """Every CLI test runs against a clean platformdirs-equivalent layout."""
    yield isolated_state_dir


@pytest.fixture(autouse=True)
def _mock_http(
    monkeypatch: pytest.MonkeyPatch,
    mock_transport: httpx.MockTransport,
) -> None:
    """Force both client implementations to use the MockTransport router."""
    import kusyllabus.client as client_module

    real_sync = httpx.Client
    real_async = httpx.AsyncClient

    def make_sync(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs["transport"] = mock_transport
        return real_sync(*args, **kwargs)

    def make_async(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = mock_transport
        return real_async(*args, **kwargs)

    monkeypatch.setattr(client_module.httpx, "Client", make_sync)
    monkeypatch.setattr(client_module.httpx, "AsyncClient", make_async)


@pytest.fixture
def runner() -> CliRunner:
    # Click >= 8.2 no longer accepts ``mix_stderr``; stdout/stderr are split
    # by default and accessible via ``result.stdout`` / ``result.stderr``.
    return CliRunner()


def _parse_json(out: str) -> Any:
    # Typer's CliRunner captures plain stdout; orjson writes the final newline.
    return json.loads(out.strip().splitlines()[-1])


def test_top_level_help_lists_every_noun(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for noun in (
        "search",
        "syllabus",
        "all",
        "titles",
        "master",
        "profile",
        "jobs",
        "feedback",
        "agent-context",
    ):
        assert noun in result.stdout


def test_search_list_json_payload_shape(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["--json", "search", "list", "--slot", "wed1", "--limit", "3"],
    )
    assert result.exit_code == 0, result.stderr
    payload = _parse_json(result.stdout)
    assert payload["total"] == 260
    assert payload["rows_returned"] == 3
    assert payload["truncated"] is True
    assert all("lecture_no" in row for row in payload["rows"])


def test_search_list_rejects_invalid_enum(runner: CliRunner) -> None:
    """Rule 3: error must enumerate valid values."""
    result = runner.invoke(app, ["search", "list", "--language", "99"])
    assert result.exit_code == 2
    assert "--language" in result.stderr
    assert "1" in result.stderr and "4" in result.stderr  # valid range hinted


def test_search_list_rejects_page_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["search", "list", "--page", "0"])
    assert result.exit_code == 2
    assert "page" in result.stderr.lower()


def test_syllabus_get_returns_json_with_teachers(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "syllabus", "get", "63736"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["lecture_no"] == 63736
    assert payload["teachers"][0]["name"] == "Nguyen Thanh Phuc"


def test_syllabus_get_missing_returns_exit_4(runner: CliRunner) -> None:
    result = runner.invoke(app, ["syllabus", "get", "999999"])
    assert result.exit_code == 4
    assert "not found" in result.stderr


def test_syllabus_get_missing_json_emits_null(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "syllabus", "get", "999999"])
    # With --json we emit `null` on stdout AND exit 4.
    assert result.exit_code == 4
    assert result.stdout.strip().splitlines()[-1] == "null"


def test_all_leaves_filter_by_kind(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "all", "leaves", "--kind", "open", "--limit", "5"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["truncated"] is True
    assert payload["rows_returned"] == 5
    assert all(leaf["kind"] == "open_syllabus" for leaf in payload["leaves"])


def test_titles_list_for_dept_80(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "titles", "list", "-d", "80"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["department_no"] == 80
    assert payload["count"] >= 1


def test_master_departments_json(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "master", "departments"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["enum"] == "departments"
    assert any(m["value"] == 80 for m in payload["members"])


def test_profile_save_then_use(runner: CliRunner) -> None:
    # 1. Save a profile
    saved = runner.invoke(
        app,
        ["--json", "profile", "save", "wed-en", "--language", "2", "--slot-index", "31", "--force"],
    )
    assert saved.exit_code == 0
    payload = _parse_json(saved.stdout)
    assert payload["saved"]["name"] == "wed-en"

    # 2. List shows it
    listed = runner.invoke(app, ["--json", "profile", "list"])
    assert listed.exit_code == 0
    names = [p["name"] for p in _parse_json(listed.stdout)["profiles"]]
    assert "wed-en" in names

    # 3. Use it in a search
    used = runner.invoke(app, ["--json", "--profile", "wed-en", "search", "count"])
    assert used.exit_code == 0
    payload = _parse_json(used.stdout)
    assert payload["total"] >= 0  # router returns 260 for wed1


def test_profile_save_existing_requires_force(runner: CliRunner) -> None:
    runner.invoke(app, ["profile", "save", "dup"])
    second = runner.invoke(app, ["profile", "save", "dup"])
    assert second.exit_code == 2
    assert "--force" in second.stderr


def test_profile_delete_requires_force(runner: CliRunner) -> None:
    runner.invoke(app, ["profile", "save", "delme"])
    no_force = runner.invoke(app, ["profile", "delete", "delme"])
    assert no_force.exit_code == 2
    forced = runner.invoke(app, ["profile", "delete", "delme", "--force"])
    assert forced.exit_code == 0


def test_jobs_list_empty(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "jobs", "list"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["jobs"] == []


def test_feedback_round_trip(runner: CliRunner) -> None:
    added = runner.invoke(app, ["--json", "feedback", "add", "ci smoke test"])
    assert added.exit_code == 0
    payload = _parse_json(added.stdout)
    assert payload["entry"]["text"] == "ci smoke test"

    listed = runner.invoke(app, ["--json", "feedback", "list"])
    assert listed.exit_code == 0
    entries = _parse_json(listed.stdout)["entries"]
    assert any(e["text"] == "ci smoke test" for e in entries)


def test_agent_context_shape(runner: CliRunner) -> None:
    result = runner.invoke(app, ["agent-context"])
    assert result.exit_code == 0
    payload = _parse_json(result.stdout)
    assert payload["schema_version"] == "1"
    assert "search" in payload["commands"]["subcommands"]
    assert "departments" in payload["masters"]
    assert "stdout" in payload["delivery_schemes"]
    # Per Rule 9, profile names are surfaced through agent-context.
    assert isinstance(payload["available_profiles"], list)


def test_syllabus_fetch_all_writes_jsonl(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "syllabi.jsonl"
    result = runner.invoke(
        app,
        [
            "--json",
            "syllabus",
            "fetch-all",
            "--out",
            str(out),
            "--kind",
            "open",
            "--limit",
            "2",
            "--concurrency",
            "2",
            "--rps",
            "10",
            "--force",
        ],
    )
    assert result.exit_code == 0, result.stderr
    payload = _parse_json(result.stdout)
    assert payload["done"] == 2
    assert out.exists()
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert "lecture_no" in record


def test_syllabus_fetch_all_refuses_to_overwrite_without_force(
    runner: CliRunner, tmp_path: Path
) -> None:
    out = tmp_path / "syllabi.jsonl"
    out.write_text("placeholder\n")
    result = runner.invoke(
        app,
        ["syllabus", "fetch-all", "--out", str(out), "--limit", "1"],
    )
    assert result.exit_code == 2
    assert "--force" in result.stderr
