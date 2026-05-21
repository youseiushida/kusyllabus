"""Tests for SearchCondition's query-building behaviour."""

from __future__ import annotations

import pytest

from kusyllabus.conditions import SearchCondition
from kusyllabus.enums import DayOfWeek, DepartmentNo, LanguageNo


def _to_dict(params: list[tuple[str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for k, v in params:
        out.setdefault(k, []).append(v)
    return out


def test_empty_condition_emits_blank_browser_form() -> None:
    """An untouched SearchCondition must mirror the recorded HAR shape:
    every condition.* key present with an empty value, no weekSchedule, and
    syutyu=false. Anything else and we drift from the live form payload."""
    cond = SearchCondition()
    params = cond.to_query_params()
    keys = [k for k, _ in params]
    for required in (
        "condition.departmentNo",
        "condition.openSyllabusTitle",
        "condition.openSyllabusTitleEn",
        "condition.courseNumberingJugyokeitaiNo",
        "condition.courseNumberingLanguageNo",
        "condition.semesterNo",
        "condition.courseNumberingLevelNo",
        "condition.courseNumberingBunkaNo",
        "condition.teacherName",
        "condition.teacherNameEn",
        "condition.keyword",
        "condition.keywordEn",
        "condition.syutyu",
    ):
        assert required in keys
    # syutyu defaults to false, not blank.
    d = _to_dict(params)
    assert d["condition.syutyu"] == ["false"]
    # No weekSchedule keys when nothing is added.
    assert not any(k.startswith("condition.weekSchedule") for k in keys)


def test_add_slot_records_xy_index() -> None:
    cond = SearchCondition()
    cond.add_slot(DayOfWeek.WEDNESDAY, 1)
    cond.add_slot(DayOfWeek.MONDAY, 2)
    assert cond.week_schedule == {31, 12}
    params = cond.to_query_params()
    week_keys = [k for k, _ in params if k.startswith("condition.weekSchedule")]
    # Always emitted sorted so the wire shape is deterministic.
    assert week_keys == ["condition.weekSchedule[12]", "condition.weekSchedule[31]"]
    assert all(v == "true" for k, v in params if k.startswith("condition.weekSchedule"))


def test_enum_coercion_renders_integer_value() -> None:
    cond = SearchCondition(
        department_no=DepartmentNo.LIBERAL_ARTS,
        language_no=LanguageNo.ENGLISH,
    )
    params = dict(cond.to_query_params())
    assert params["condition.departmentNo"] == "80"
    assert params["condition.courseNumberingLanguageNo"] == "2"


def test_page_appended_when_provided() -> None:
    cond = SearchCondition()
    params = cond.to_query_params(page=3)
    assert ("page", "3") in params


def test_page_must_be_positive() -> None:
    cond = SearchCondition()
    with pytest.raises(ValueError, match="page must be >= 1"):
        cond.to_query_params(page=0)
    with pytest.raises(ValueError):
        cond.to_query_params(page=-1)


def test_bunka_no_validation() -> None:
    # 86 is the upper bound observed in the live `<select>`.
    SearchCondition(bunka_no=86)
    SearchCondition(bunka_no=1)
    with pytest.raises(ValueError):
        SearchCondition(bunka_no=87)
    with pytest.raises(ValueError):
        SearchCondition(bunka_no=0)


def test_add_slots_bulk() -> None:
    cond = SearchCondition().add_slots([(DayOfWeek.MONDAY, 1), (DayOfWeek.TUESDAY, 2)])
    assert cond.week_schedule == {11, 22}
