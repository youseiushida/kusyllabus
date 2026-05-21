"""Tests for the pydantic model shapes."""

from __future__ import annotations

import json

from kusyllabus.models import (
    AllTreeNode,
    SearchResult,
    SearchResultRow,
    Syllabus,
    SyllabusTitleOption,
    Teacher,
)


def test_syllabus_minimal_construction() -> None:
    syl = Syllabus(lecture_no=12345)
    assert syl.lecture_no == 12345
    assert syl.display_lang == "ja"
    assert syl.teachers == []
    assert syl.related_urls == []


def test_syllabus_serialises_round_trip() -> None:
    syl = Syllabus(
        lecture_no=42,
        title="X",
        teachers=[Teacher(department="工学研究科", job_title="教授", name="名無し")],
        days_and_periods="水1",
        related_urls=["https://example.com"],
        raw_labels={"科目ナンバリング": "U-LAS00 00000 LJ00"},
    )
    encoded = syl.model_dump(mode="json")
    decoded = Syllabus.model_validate(json.loads(json.dumps(encoded)))
    assert decoded == syl


def test_search_result_page_count_math() -> None:
    sr = SearchResult(total=260, page=1)
    # 260 / 10 = 26 pages.
    assert sr.page_count == 26
    assert SearchResult(total=0, page=1).page_count == 0
    assert SearchResult(total=11, page=1).page_count == 2


def test_search_result_row_defaults_arrays() -> None:
    row = SearchResultRow(lecture_no=1, title="t")
    assert row.instructors == []
    assert row.days_and_periods == []
    assert row.academic_fields == []


def test_all_tree_node_distinguishes_kinds() -> None:
    branch = AllTreeNode(name="dept")
    open_leaf = AllTreeNode(name="L1", lecture_no=61323, kind="open_syllabus")
    dept_leaf = AllTreeNode(
        name="L2", lecture_no=26510, department_no=1, kind="department_syllabus"
    )
    assert branch.lecture_no is None
    assert open_leaf.department_no is None
    assert dept_leaf.department_no == 1


def test_syllabus_title_option_keeps_string_value() -> None:
    opt = SyllabusTitleOption(
        value="人文・社会科学科目群／哲学・思想", label="人文・社会科学科目群／哲学・思想"
    )
    # Real-world value is a label string, not an integer code.
    assert isinstance(opt.value, str)
    assert "／" in opt.value
