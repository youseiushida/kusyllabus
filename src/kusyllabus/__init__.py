"""kusyllabus — Kyoto University open syllabus client library.

The Kyoto University open syllabus (https://www.k.kyoto-u.ac.jp/external/open_syllabus/)
exposes its data only as Shift_JIS (windows-31j) HTML. This library wraps that
quirky surface in typed Python: pydantic models for queries and results, both
sync and async clients, and selectolax-based parsers.
"""

from kusyllabus.client import (
    AsyncKuSyllabusClient,
    KuSyllabusClient,
    flatten_all_leaves,
)
from kusyllabus.conditions import SearchCondition
from kusyllabus.enums import (
    DayOfWeek,
    DepartmentNo,
    JugyokeitaiNo,
    LanguageNo,
    LevelNo,
    SemesterNo,
)
from kusyllabus.exceptions import (
    KuSyllabusError,
    KuSyllabusHTTPError,
    KuSyllabusParseError,
    SyllabusNotFound,
)
from kusyllabus.models import (
    AllTreeNode,
    SearchResult,
    SearchResultRow,
    Syllabus,
    SyllabusTitleOption,
    Teacher,
)

__all__ = [
    "AllTreeNode",
    "AsyncKuSyllabusClient",
    "DayOfWeek",
    "DepartmentNo",
    "JugyokeitaiNo",
    "KuSyllabusClient",
    "KuSyllabusError",
    "KuSyllabusHTTPError",
    "KuSyllabusParseError",
    "LanguageNo",
    "LevelNo",
    "SearchCondition",
    "SearchResult",
    "SearchResultRow",
    "SemesterNo",
    "Syllabus",
    "SyllabusNotFound",
    "SyllabusTitleOption",
    "Teacher",
    "flatten_all_leaves",
]
