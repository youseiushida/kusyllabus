"""Tests that drive every parser with recorded fixture HTML.

Detroit-school: no mocks. We feed real bytes through the real parsers and
assert the resulting pydantic models.
"""

from __future__ import annotations

from collections.abc import Callable

from kusyllabus.parsers import (
    parse_all_tree,
    parse_search_result,
    parse_syllabus,
    parse_syllabus_titles,
)


def test_parse_syllabus_japanese(fixture_text: Callable[[str], str]) -> None:
    syl = parse_syllabus(fixture_text("la_63736.html"), lecture_no=63736)
    assert syl.lecture_no == 63736
    assert syl.display_lang == "ja"
    assert syl.course_numbers == ["U-LAS13 10004 LE60"]
    assert syl.course_number == "U-LAS13 10004 LE60"  # convenience shorthand
    assert syl.title == "Basic Physical Chemistry (thermodynamics)-E2"
    assert syl.title_en == "Basic Physical Chemistry (thermodynamics)-E2"
    assert syl.language == "英語"
    assert syl.credits == "2単位"
    assert syl.class_style == "講義"
    assert syl.year_semester == "2026・後期"
    assert syl.days_and_periods == "水1"
    assert syl.teachers == [
        type(syl.teachers[0])(department="工学研究科", job_title="講師", name="Nguyen Thanh Phuc")
    ]
    assert (syl.overview_purpose or "").startswith("Physical chemistry is the discipline")
    assert syl.related_urls == []
    assert syl.youtube_movie_ids == []
    # Sanity: every label we recognised landed in raw_labels too.
    assert "科目ナンバリング" in syl.raw_labels
    assert "授業の概要・目的" in syl.raw_labels


def test_parse_syllabus_english(fixture_text: Callable[[str], str]) -> None:
    syl = parse_syllabus(fixture_text("la_63736_en.html"), lecture_no=63736, display_lang="en")
    assert syl.display_lang == "en"
    assert syl.title == "Basic Physical Chemistry (thermodynamics)-E2"
    assert syl.class_style == "Lecture"
    assert syl.language == "English"
    assert syl.year_semester == "2026・Second semester"
    assert syl.days_and_periods == "Wed.1"
    assert syl.teachers[0].department == "Graduate School of Engineering"
    assert syl.teachers[0].job_title == "Senior Lecturer"


def test_parse_syllabus_japanese_multi_paragraph_overview(
    fixture_text: Callable[[str], str],
) -> None:
    syl = parse_syllabus(fixture_text("la_62409.html"), lecture_no=62409)
    assert syl.title == "社会学Ｉ"
    assert syl.title_en == "Sociology I"
    # Parser normalises full-width spaces ('朴　沙羅') to ordinary space.
    assert syl.teachers[0].name.startswith("朴")
    assert syl.teachers[0].name.endswith("沙羅")
    # Paragraph contents survive the parse (long form text).
    assert len(syl.overview_purpose or "") > 200


def test_parse_syllabus_department_endpoint(fixture_text: Callable[[str], str]) -> None:
    """``/department_syllabus`` shares the same DOM shape as ``/la_syllabus``."""
    syl = parse_syllabus(fixture_text("department_syllabus_sample.html"), lecture_no=26510)
    assert syl.title.startswith("国語学")
    assert syl.year_semester == "2026・前期"
    assert syl.teachers[0].department == "文学研究科"
    assert syl.teachers[0].job_title == "准教授"
    # `主要授業科目（学部・学科名）` should alias to essential_courses
    # (a `/department_syllabus`-specific label spelling).
    assert "主要授業科目（学部・学科名）" in syl.raw_labels
    assert syl.essential_courses is not None


def test_parse_syllabus_multiple_course_numbers(fixture_text: Callable[[str], str]) -> None:
    """Cross-listed courses render multiple `<br/>`-separated course numbers.

    Real-world example: ``department_syllabus?lectureNo=13355&departmentNo=16``
    lists both ``U-ENG29 39074 LJ10`` and ``U-ENG29 39074 LJ55``.
    """
    syl = parse_syllabus(fixture_text("dept_multi_course_number.html"), lecture_no=13355)
    assert syl.course_numbers == ["U-ENG29 39074 LJ10", "U-ENG29 39074 LJ55"]
    # Backwards-compatible shorthand still returns the first entry.
    assert syl.course_number == "U-ENG29 39074 LJ10"


def test_parse_search_result_count_and_rows(fixture_text: Callable[[str], str]) -> None:
    result = parse_search_result(fixture_text("search_wed1.html"), page=1)
    assert result.total == 260
    assert result.page_count == 26
    assert len(result.rows) == 10
    first = result.rows[0]
    assert first.lecture_no == 61585
    # /la_syllabus rows have no department_no.
    assert first.department_no is None
    assert first.title.startswith("The History of Eastern Thought I-E2")
    assert first.department == "全学共通科目"
    assert first.semester == "前期"
    assert first.days_and_periods == ["水1"]
    assert result.has_next_page is True
    assert result.has_prev_page is False


def test_parse_search_result_captures_department_no_for_dept_syllabus(
    fixture_text: Callable[[str], str],
) -> None:
    """Regression for the lectureNo-collision bug.

    /search rows mix two link shapes; lectureNo alone is ambiguous because the
    upstream reuses IDs between the la_syllabus and department_syllabus pools
    across years. The parser MUST surface department_no per row so callers
    pass the right path to /la_syllabus vs /department_syllabus.
    """
    result = parse_search_result(fixture_text("search_mixed_links.html"), page=1)
    by_lecture = {row.lecture_no: row for row in result.rows}

    # /la_syllabus rows: department_no is None.
    open_row = by_lecture.get(64363)
    assert open_row is not None
    assert open_row.department_no is None

    # /department_syllabus rows: department_no harvested from the href.
    dept_row = by_lecture.get(8961)
    assert dept_row is not None
    assert dept_row.department_no == 10  # 理学部
    assert all(
        row.department_no == 10 for row in result.rows if row.lecture_no in {8961, 9090, 9091, 8962}
    )


def test_parse_search_result_english(fixture_text: Callable[[str], str]) -> None:
    result = parse_search_result(fixture_text("search_en_p1.html"), page=1)
    assert result.total > 0
    assert any("Philosophy" in row.title for row in result.rows)
    # English semester label.
    assert any(row.semester in {"First semester", "Second semester"} for row in result.rows)


def test_parse_syllabus_titles_for_liberal_arts(fixture_text: Callable[[str], str]) -> None:
    options = parse_syllabus_titles(fixture_text("titles_dept80.html"))
    # The placeholder ---- option is dropped; only real categories remain.
    assert all(o.value for o in options)
    assert any("哲学" in o.value for o in options)
    assert len(options) >= 50  # observed 60+


def test_parse_syllabus_titles_for_letters(fixture_text: Callable[[str], str]) -> None:
    options = parse_syllabus_titles(fixture_text("titles_dept1.html"))
    values = {o.value for o in options}
    assert "哲学" in values
    assert "言語学" in values


def test_parse_all_tree_counts(fixture_text: Callable[[str], str]) -> None:
    """The /all page renders every department, even those without public syllabi."""
    tree = parse_all_tree(fixture_text("all.html"))
    assert len(tree) == 32
    assert tree[0].name == "全学共通科目"
    # Sum leaves across the whole tree.
    leaves = [leaf for d in tree for t in d.children for leaf in t.children]
    open_count = sum(1 for leaf in leaves if leaf.kind == "open_syllabus")
    dept_count = sum(1 for leaf in leaves if leaf.kind == "department_syllabus")
    assert open_count == 3105
    assert dept_count == 8566


def test_parse_all_tree_department_links_carry_department_no(
    fixture_text: Callable[[str], str],
) -> None:
    tree = parse_all_tree(fixture_text("all.html"))
    letters = next(d for d in tree if d.name == "文学部")
    leaves = [leaf for t in letters.children for leaf in t.children]
    assert leaves, "expected at least one leaf under 文学部"
    assert all(leaf.kind == "department_syllabus" for leaf in leaves)
    assert all(leaf.department_no is not None for leaf in leaves)
