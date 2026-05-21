"""Parser for ``/search`` result pages."""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from kusyllabus.exceptions import KuSyllabusParseError
from kusyllabus.models import SearchResult, SearchResultRow
from kusyllabus.parsers._util import extract_lecture_no, lines_from, text_of

# JP form: `検索結果は全部で<b>NN</b>件です。`
# EN form: `Search result is total of <b>NN</b>.`
_TOTAL_JP_RE = re.compile(r"<b>(\d+)</b>件")
_TOTAL_EN_RE = re.compile(r"total of <b>(\d+)</b>", re.IGNORECASE)
_DEPARTMENT_NO_RE = re.compile(r"departmentNo=(\d+)")


def parse_search_result(html: str, *, page: int) -> SearchResult:
    """Parse a /search response into a :class:`SearchResult`.

    ``page`` is supplied by the caller because the server doesn't always echo
    the current page back in a machine-readable way.
    """
    tree = HTMLParser(html)

    total = _extract_total(html)
    rows = _extract_rows(tree)

    pager_links = tree.css("a.pager_link")
    pager_pages: list[int] = []
    for a in pager_links:
        href = a.attributes.get("href") or ""
        m = re.search(r"page=(\d+)", href)
        if m:
            pager_pages.append(int(m.group(1)))

    has_next = any(p > page for p in pager_pages)
    has_prev = any(p < page for p in pager_pages)

    return SearchResult(
        total=total,
        page=page,
        rows=rows,
        has_next_page=has_next,
        has_prev_page=has_prev,
    )


def _extract_total(html: str) -> int:
    m = _TOTAL_JP_RE.search(html) or _TOTAL_EN_RE.search(html)
    if not m:
        # An over-paged response (e.g. page=999) silently drops the count.
        return 0
    return int(m.group(1))


def _extract_rows(tree: HTMLParser) -> list[SearchResultRow]:
    """Extract data rows from ``<table class="standard_list">``."""
    rows: list[SearchResultRow] = []
    for tr in tree.css("table.standard_list tr.odd_normal, table.standard_list tr.even_normal"):
        cells = tr.css("td")
        # Expected layout: 11 cells (10 data + 1 detail-button).
        if len(cells) < 11:
            continue

        # Cell 0: title (single line).
        title = text_of(cells[0])

        # Cell 1: instructors, separated by <br/>.
        instructors = lines_from(cells[1])

        # Cell 2-6 single line text.
        department = text_of(cells[2])
        department_group = text_of(cells[3])
        class_style = text_of(cells[4])
        language = text_of(cells[5])
        semester = text_of(cells[6])

        # Cell 7: days/periods, possibly multi-line.
        days_and_periods = lines_from(cells[7])

        # Cell 8: level.
        level = text_of(cells[8])

        # Cell 9: academic fields, possibly multi-line.
        academic_fields = lines_from(cells[9])

        # Cell 10: detail link. /search rows mix two link shapes:
        #   la_syllabus?lectureNo=N             → open syllabus, no department_no
        #   department_syllabus?lectureNo=N&departmentNo=D → faculty syllabus
        # We MUST capture department_no when present; otherwise an agent will
        # call /la_syllabus?lectureNo=N and either 404 or — far worse — receive
        # a stale row with the same lectureNo recycled across years.
        a = cells[10].css_first("a")
        href = (a.attributes.get("href") if a is not None else None) or ""
        lecture_no = extract_lecture_no(href)
        if lecture_no is None:
            # If this row's detail link is missing, skip — without it the row
            # is unusable for follow-up fetches.
            continue
        department_no: int | None = None
        if href.startswith("department_syllabus"):
            m = _DEPARTMENT_NO_RE.search(href)
            if m:
                department_no = int(m.group(1))

        rows.append(
            SearchResultRow(
                lecture_no=lecture_no,
                department_no=department_no,
                title=title,
                instructors=instructors,
                department=department,
                department_group=department_group,
                class_style=class_style,
                language=language,
                semester=semester,
                days_and_periods=days_and_periods,
                level=level,
                academic_fields=academic_fields,
            )
        )
    return rows


def _assert_table_present(tree: HTMLParser) -> None:
    """Sanity check used only by tests to detect totally unexpected payloads."""
    if not tree.css("table.standard_list"):
        raise KuSyllabusParseError("No <table class='standard_list'> found in search response")
