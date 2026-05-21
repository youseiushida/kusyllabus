"""Live integration tests hitting the real Kyoto University open syllabus.

These tests detect upstream schema drift early. They are excluded from the
default collection — opt in with ``pytest -m live`` (CI runs them only on
manual workflow_dispatch).

Conventions:

* Single-request endpoints only; we never crawl the full ``/all`` tree here.
* Each test asserts only the *contract* (shape, presence of fields, count
  ranges) rather than exact strings — the upstream content changes year to
  year as syllabi are updated.
* Network errors propagate; they aren't dressed up. A CI failure here means
  the upstream changed or is unreachable.
"""

from __future__ import annotations

import pytest

from kusyllabus import KuSyllabusClient, SearchCondition
from kusyllabus.enums import DayOfWeek, LanguageNo

pytestmark = pytest.mark.live


def test_top_page_returns_html_in_cp932() -> None:
    with KuSyllabusClient() as ku:
        html = ku.get_top_html()
    assert html  # non-empty
    assert "京都大学教務情報システム" in html or "シラバス検索" in html


def test_search_wed1_returns_known_minimum() -> None:
    """The Wednesday-1 corpus historically holds 200+ matches.

    If this falls below 100 the upstream pruned a lot of slots; investigate.
    """
    with KuSyllabusClient() as ku:
        cond = SearchCondition().add_slot(DayOfWeek.WEDNESDAY, 1)
        result = ku.search(cond, page=1)
    assert result.total >= 100
    assert len(result.rows) == 10  # page size is fixed upstream
    assert all(row.lecture_no > 0 for row in result.rows)


def test_search_english_language_filter() -> None:
    with KuSyllabusClient() as ku:
        cond = SearchCondition(language_no=LanguageNo.ENGLISH)
        result = ku.search(cond, page=1)
    assert result.total >= 100
    assert any(row.language == "英語" for row in result.rows)


def test_get_open_syllabus_titles_for_liberal_arts() -> None:
    """Dropdown values for the liberal-arts department should be 30+."""
    with KuSyllabusClient() as ku:
        options = ku.get_syllabus_titles(80)
    assert len(options) >= 30
    assert all(o.value for o in options)


def test_get_one_open_syllabus_via_all_tree() -> None:
    """Pull the first leaf out of /all and fetch its detail page."""
    with KuSyllabusClient() as ku:
        tree = ku.get_all_tree()
        # First liberal-arts leaf with a stable lectureNo.
        first_dept = tree[0]
        first_title = first_dept.children[0]
        first_leaf = next(
            (
                leaf
                for leaf in first_title.children
                if leaf.kind == "open_syllabus" and leaf.lecture_no
            ),
            None,
        )
        assert first_leaf is not None
        syllabus = ku.get_syllabus(first_leaf.lecture_no)
    assert syllabus is not None
    assert syllabus.course_number  # every open syllabus has a course number
    assert syllabus.teachers, "every open syllabus should list at least one teacher"


def test_missing_lecture_number_returns_none() -> None:
    """5xx-or-404 differentiation: nonexistent IDs return None, not raise."""
    with KuSyllabusClient() as ku:
        assert ku.get_syllabus(1) is None  # lectureNo=1 is below the live range


def test_all_tree_has_three_levels_and_thousands_of_leaves() -> None:
    """/all is the load-bearing endpoint for `fetch-all` and the agent skill."""
    with KuSyllabusClient() as ku:
        tree = ku.get_all_tree()
    assert len(tree) >= 30  # 32 departments observed; allow a small wobble
    total_leaves = sum(
        1 for d in tree for t in d.children for leaf in t.children if leaf.lecture_no
    )
    assert total_leaves >= 8_000
