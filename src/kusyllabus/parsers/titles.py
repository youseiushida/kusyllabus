"""Parser for ``/open_syllabus_titles?departmentNo=N``."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from kusyllabus.models import SyllabusTitleOption


def parse_syllabus_titles(html: str) -> list[SyllabusTitleOption]:
    """Parse the option list fragment returned by ``/open_syllabus_titles``.

    The placeholder ``<option value="" class="form_disable">----</option>`` is
    omitted from the result.
    """
    tree = HTMLParser(html)
    options: list[SyllabusTitleOption] = []
    for opt in tree.css("option"):
        value = opt.attributes.get("value") or ""
        label = (opt.text(deep=True) or "").strip()
        if not value:
            continue
        options.append(SyllabusTitleOption(value=value, label=label))
    return options
