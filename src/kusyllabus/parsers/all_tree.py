"""Parser for the ``/all`` page (3-level Department → OpenTitle → Syllabi tree)."""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser, Node

from kusyllabus.models import AllTreeNode
from kusyllabus.parsers._util import extract_lecture_no, text_of

_DEPARTMENT_NO_RE = re.compile(r"departmentNo=(\d+)")


def parse_all_tree(html: str) -> list[AllTreeNode]:
    """Return a list of department-level :class:`AllTreeNode` roots.

    The /all page lays out one ``.departmentName`` heading per department,
    followed by a sibling ``.departmentSection`` whose ``.openTitle`` /
    ``.syllabusTitle`` children form the rest of the tree.
    """
    tree = HTMLParser(html)
    roots: list[AllTreeNode] = []

    for dept_name in tree.css(".departmentName"):
        dept = AllTreeNode(name=_strip_icon(text_of(dept_name)))
        # The actual list lives in the next .departmentSection sibling.
        section = _next_section(dept_name)
        if section is not None:
            dept.children.extend(_parse_section(section))
        roots.append(dept)

    return roots


def _next_section(dept_name: Node) -> Node | None:
    parent = dept_name.parent
    if parent is None:
        return None
    return parent.css_first(".departmentSection")


def _parse_section(section: Node) -> list[AllTreeNode]:
    """For each .openTitle/.syllabusses pair inside this section, build a node."""
    children: list[AllTreeNode] = []
    for open_title in section.css(".openTitle"):
        node = AllTreeNode(name=_strip_icon(text_of(open_title)))
        # The matching <div class="syllabusses"> lives among the openTitle's siblings.
        syllabusses = _matching_syllabusses(open_title)
        if syllabusses is not None:
            for a in syllabusses.css(".syllabusTitle a"):
                href = a.attributes.get("href") or ""
                lecture_no = extract_lecture_no(href)
                if lecture_no is None:
                    continue
                if href.startswith("la_syllabus"):
                    kind = "open_syllabus"
                    department_no = None
                elif href.startswith("department_syllabus"):
                    kind = "department_syllabus"
                    m = _DEPARTMENT_NO_RE.search(href)
                    department_no = int(m.group(1)) if m else None
                else:
                    # Unknown leaf shape; record it but mark as branch so callers
                    # can choose to ignore.
                    kind = "branch"
                    department_no = None
                node.children.append(
                    AllTreeNode(
                        name=text_of(a),
                        lecture_no=lecture_no,
                        department_no=department_no,
                        kind=kind,
                    )
                )
        children.append(node)
    return children


def _matching_syllabusses(open_title: Node) -> Node | None:
    """Return the ``<div class='syllabusses'>`` immediately following ``open_title``
    within the same parent ``<div>``."""
    parent = open_title.parent
    if parent is None:
        return None
    return parent.css_first(".syllabusses")


def _strip_icon(text: str) -> str:
    """Department/openTitle headings end with ``＋`` icon; drop trailing markers."""
    return text.rstrip("＋ー―+-—").strip()
