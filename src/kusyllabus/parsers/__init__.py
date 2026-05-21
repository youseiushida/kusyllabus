"""HTML parsers for the open-syllabus pages.

Each module exports a single ``parse_*`` function that accepts the response
body (already decoded as CP932) and returns a typed model from
:mod:`kusyllabus.models`.
"""

from kusyllabus.parsers.all_tree import parse_all_tree
from kusyllabus.parsers.search import parse_search_result
from kusyllabus.parsers.syllabus import parse_syllabus
from kusyllabus.parsers.titles import parse_syllabus_titles

__all__ = [
    "parse_all_tree",
    "parse_search_result",
    "parse_syllabus",
    "parse_syllabus_titles",
]
