"""Tests for the master enums and the day/period helper."""

from __future__ import annotations

import pytest

from kusyllabus.enums import (
    BUNKA_NAMES_EN,
    BUNKA_NAMES_JP,
    DayOfWeek,
    DepartmentNo,
    JugyokeitaiNo,
    LanguageNo,
    LevelNo,
    SemesterNo,
    bunka_label,
    parse_day_period_label,
    week_schedule_index,
)


def test_department_labels_round_trip() -> None:
    assert DepartmentNo.LIBERAL_ARTS.label_jp == "全学共通科目"
    assert DepartmentNo.LIBERAL_ARTS.label_en == "Liberal Arts and General Education Courses"
    assert DepartmentNo.from_label("文学部", "ja") is DepartmentNo.LETTERS
    assert DepartmentNo.from_label("Faculty of Letters", "en") is DepartmentNo.LETTERS
    assert DepartmentNo.from_label("unknown") is None


def test_department_no_includes_all_32_members() -> None:
    # If this count drifts, the upstream added/removed a department and we
    # need to regenerate the enum.
    assert len(list(DepartmentNo)) == 32


def test_jugyokeitai_labels() -> None:
    assert JugyokeitaiNo.LECTURE.label_jp == "講義"
    assert JugyokeitaiNo.LECTURE.label_en == "Lecture"


def test_language_labels() -> None:
    assert LanguageNo.ENGLISH.label_jp == "英語"
    assert LanguageNo.ENGLISH.label_en == "English"


def test_semester_includes_irregular_17() -> None:
    # SemesterNo.SECOND_THEN_FIRST == 17, the only non-sequential value.
    assert SemesterNo.SECOND_THEN_FIRST.value == 17


def test_level_count() -> None:
    assert len(list(LevelNo)) == 9


@pytest.mark.parametrize(
    ("day", "period", "expected"),
    [
        (DayOfWeek.WEDNESDAY, 1, 31),
        (DayOfWeek.MONDAY, 5, 15),
        (DayOfWeek.FRIDAY, 3, 53),
        (DayOfWeek.SATURDAY, 1, 61),
    ],
)
def test_week_schedule_index(day: DayOfWeek, period: int, expected: int) -> None:
    assert week_schedule_index(day, period) == expected


@pytest.mark.parametrize("period", [0, 6, -1])
def test_week_schedule_index_rejects_invalid_period(period: int) -> None:
    with pytest.raises(ValueError):
        week_schedule_index(DayOfWeek.MONDAY, period)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("水1", (DayOfWeek.WEDNESDAY, 1)),
        ("月5", (DayOfWeek.MONDAY, 5)),
        ("Wed.1", (DayOfWeek.WEDNESDAY, 1)),
        ("Fri.3", (DayOfWeek.FRIDAY, 3)),
    ],
)
def test_parse_day_period_label(label: str, expected: tuple[DayOfWeek, int]) -> None:
    assert parse_day_period_label(label) == expected


def test_parse_day_period_label_returns_none_on_garbage() -> None:
    assert parse_day_period_label("garbage") is None


def test_bunka_master_complete() -> None:
    assert len(BUNKA_NAMES_JP) == 86
    assert len(BUNKA_NAMES_EN) == 86
    assert set(BUNKA_NAMES_JP) == set(range(1, 87))


def test_bunka_label_lookup() -> None:
    assert bunka_label(25, "ja") == "哲学"
    assert bunka_label(25, "en") == "Philosophy"
    assert bunka_label(999, "ja") is None
