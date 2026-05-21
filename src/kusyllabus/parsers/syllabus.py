"""Parser for ``/la_syllabus?lectureNo=N`` detail pages."""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser, Node

from kusyllabus.models import Syllabus, Teacher
from kusyllabus.parsers._util import lines_from, text_of

_LABEL_PAREN_RE = re.compile(r"\(([^)]+)\)")
_NESTED_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_WS_RE = re.compile(r"\s+")

# (label) → Syllabus attribute name. Both Japanese and English page variants
# are normalised into the same set of attributes (we keep the original page
# language in Syllabus.display_lang).
_JP_LABELS: dict[str, str] = {
    "科目ナンバリング": "course_number",
    "科目名": "title",
    "英 訳": "title_en",
    "使用言語": "language",
    "単位数": "credits",
    "授業形態": "class_style",
    "開講年度・開講期": "year_semester",
    "配当学年": "target_year",
    "対象学生": "eligible_students",
    "曜時限": "days_and_periods",
    "授業の概要・目的": "overview_purpose",
    "到達目標": "objectives",
    "授業計画と内容": "schedule_and_contents",
    "履修要件": "requirements",
    "成績評価の方法・観点": "evaluation",
    "教科書": "textbooks",
    "参考書等": "references",
    "授業外学修（予習・復習）等": "study_outside_of_class",
    "主要授業科目": "essential_courses",
    # 関連URL is handled specially via reference-url anchors.
}

_EN_LABELS: dict[str, str] = {
    "Course number": "course_number",
    "Course title": "title",
    "Language of instruction": "language",
    "Number of credits": "credits",
    "Class style": "class_style",
    "Year/semesters": "year_semester",
    "Target year": "target_year",
    "Eligible students": "eligible_students",
    "Days and periods": "days_and_periods",
    "Overview and purpose of the course": "overview_purpose",
    "Course objectives": "objectives",
    "Course schedule and contents": "schedule_and_contents",
    "Course requirements": "requirements",
    "Evaluation methods and policy": "evaluation",
    "Textbooks": "textbooks",
    "References, etc.": "references",
    "Study outside of class": "study_outside_of_class",
    "Essential courses": "essential_courses",
}


def parse_syllabus(html: str, *, lecture_no: int, display_lang: str = "ja") -> Syllabus:
    """Parse a syllabus detail page.

    ``lecture_no`` and ``display_lang`` are supplied by the caller because the
    detail HTML does not always echo them in a machine-friendly form.
    """
    tree = HTMLParser(html)
    label_map = _EN_LABELS if display_lang == "en" else _JP_LABELS

    raw_labels: dict[str, str] = {}
    field_values: dict[str, str] = {}

    for label_node in tree.css(".lesson_plan_subheading"):
        label = _clean_label(text_of(label_node))
        if not label:
            continue
        value_node = _value_node_for(label_node)
        if value_node is None:
            continue
        value = _value_text(value_node)
        raw_labels[label] = value

        attr_name = _resolve_label(label, label_map)
        if attr_name is None:
            continue
        # First occurrence wins (some labels may appear twice in nested tables).
        field_values.setdefault(attr_name, value)

    teachers = _extract_teachers(tree, display_lang=display_lang)
    related_urls = [
        (a.attributes.get("href") or "").strip()
        for a in tree.css("a.reference-url")
        if (a.attributes.get("href") or "").strip()
    ]
    youtube_ids = [
        (n.attributes.get("data-movie-id") or "").strip()
        for n in tree.css(".youtube-movie")
        if (n.attributes.get("data-movie-id") or "").strip()
    ]

    return Syllabus(
        lecture_no=lecture_no,
        display_lang=display_lang,
        teachers=teachers,
        related_urls=related_urls,
        youtube_movie_ids=youtube_ids,
        raw_labels=raw_labels,
        **field_values,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_label(text: str) -> str:
    """Return the canonical label inside ``(...)`` or an empty string.

    Some English labels include nested parens like
    ``(Course title (and course title in English))`` or
    ``(Study outside of class (preparation and review))``. We drop the outer
    pair first and then strip any *halfwidth* parenthesised tails; fullwidth
    parens used in Japanese labels (e.g. ``授業外学修（予習・復習）等``) are
    preserved.
    """
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        inner = text[1:-1]
    else:
        m = _LABEL_PAREN_RE.search(text)
        if not m:
            return ""
        inner = m.group(1)
    cleaned = _NESTED_PAREN_RE.sub(" ", inner)
    return _WS_RE.sub(" ", cleaned).strip()


def _resolve_label(label: str, label_map: dict[str, str]) -> str | None:
    if label in label_map:
        return label_map[label]
    # Fallback: try a whitespace-collapsed key (English labels can wrap).
    norm = _WS_RE.sub(" ", label).strip()
    for k, v in label_map.items():
        if _WS_RE.sub(" ", k).strip() == norm:
            return v
    # Final fallback: drop whitespace entirely, since the HTML often puts
    # `<br/>` between words with no surrounding spaces, producing
    # ``Language ofinstruction`` etc.
    squashed = _WS_RE.sub("", label)
    for k, v in label_map.items():
        if _WS_RE.sub("", k) == squashed:
            return v
    return None


def _value_node_for(label_node: Node) -> Node | None:
    """Locate the node whose text holds the label's value.

    The HTML uses two shapes:

    1. ``<td>(label)</td><td>VALUE</td>`` — value is the label cell's next ``<td>`` sibling.
    2. ``<div class="lesson_plan_subheading">(label)</div><div>VALUE</div>`` —
       value is the label div's next ``<div>`` sibling.
    """
    parent = label_node.parent
    # Shape 1: label_node is inside a <td>; look at the parent's next sibling.
    if parent is not None and parent.tag == "td":
        td_parent = parent
        sibling = _next_element_sibling(td_parent)
        if sibling is not None and sibling.tag == "td":
            return sibling
    # Shape 2: label_node is itself a <div> with the subheading class.
    if label_node.tag == "div":
        sibling = _next_element_sibling(label_node)
        if sibling is not None:
            return sibling
    # Shape 3: label inside <span> directly under another tag; try sibling text.
    if parent is not None:
        sibling = _next_element_sibling(parent)
        if sibling is not None:
            return sibling
    return None


def _next_element_sibling(node: Node) -> Node | None:
    sib = node.next
    while sib is not None and sib.tag == "-text":
        sib = sib.next
    return sib


def _value_text(node: Node) -> str:
    """Extract the user-visible text of a value node, preserving line breaks
    introduced by ``<br/>`` tags."""
    lines = lines_from(node)
    return "\n".join(lines)


def _extract_teachers(tree: HTMLParser, *, display_lang: str) -> list[Teacher]:
    """Pull instructor rows from the (所属部局/職名/氏名) sub-table.

    Locates the instructor block via a known label and then walks up to the
    enclosing ``<table>``. Handles both the 3-cell-header layout (JP page,
    one ``<span>`` per column) and the single-row-header layout (EN page,
    one ``<span>`` spanning all three columns).
    """
    teachers: list[Teacher] = []
    anchor_labels_jp = ("所属部局", "職 名", "氏 名")
    anchor_labels_en = (
        "Instructor's name, job title, and department of affiliation",
        "Instructor's name",
        "Department of affiliation",
    )

    needle = anchor_labels_en if display_lang == "en" else anchor_labels_jp
    container: Node | None = None
    for span in tree.css(".lesson_plan_subheading"):
        text = text_of(span)
        if any(label in text for label in needle):
            container = span
            while container is not None and container.tag != "table":
                container = container.parent
            if container is not None:
                break
    if container is None:
        return teachers

    for tr in container.css("tr"):
        cells = tr.css("td")
        if len(cells) != 3:
            continue
        if any(c.css_first(".lesson_plan_subheading") is not None for c in cells):
            continue
        dept, job, name = (text_of(c) for c in cells)
        if not (dept or job or name):
            continue
        teachers.append(Teacher(department=dept, job_title=job, name=name))
    return teachers
