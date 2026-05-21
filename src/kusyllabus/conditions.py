"""Pydantic model for assembling ``/search`` query parameters."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from kusyllabus.enums import (
    DayOfWeek,
    DepartmentNo,
    JugyokeitaiNo,
    LanguageNo,
    LevelNo,
    SemesterNo,
    week_schedule_index,
)


class SearchCondition(BaseModel):
    """Open-syllabus ``/search`` query.

    Every field maps 1-to-1 to a ``condition.*`` query parameter. ``None``
    fields are sent as empty values (``condition.foo=``) to mimic the browser
    form submission — the server tolerates either omitting the key or sending
    an empty value, but sending empties matches the recorded HARs and is the
    safer default.

    Build by passing values directly:

    >>> c = SearchCondition(department_no=DepartmentNo.LIBERAL_ARTS,
    ...                     language_no=LanguageNo.ENGLISH,
    ...                     keyword="thermodynamics")
    >>> c.add_slot(DayOfWeek.WEDNESDAY, 1)
    >>> sorted(c.week_schedule)
    [31]
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    department_no: DepartmentNo | int | None = None
    open_syllabus_title: str | None = None
    open_syllabus_title_en: str | None = None
    jugyokeitai_no: JugyokeitaiNo | int | None = None
    language_no: LanguageNo | int | None = None
    semester_no: SemesterNo | int | None = None
    level_no: LevelNo | int | None = None
    bunka_no: int | None = Field(default=None, ge=1, le=86)
    teacher_name: str | None = None
    teacher_name_en: str | None = None
    keyword: str | None = None
    keyword_en: str | None = None
    syutyu: bool = False
    """``True`` to filter to intensive courses only."""

    week_schedule: set[int] = Field(default_factory=set)
    """Set of ``XY`` indexes for ``condition.weekSchedule[XY]=true``.

    Multiple entries combine with OR. Use :meth:`add_slot` to populate from
    ``(DayOfWeek, period)`` pairs.
    """

    def add_slot(self, day: DayOfWeek | int, period: int) -> SearchCondition:
        """Add a (day, period) slot. Returns ``self`` for chaining."""
        self.week_schedule.add(week_schedule_index(day, period))
        return self

    def add_slots(self, slots: Iterable[tuple[DayOfWeek | int, int]]) -> SearchCondition:
        for d, p in slots:
            self.add_slot(d, p)
        return self

    def to_query_params(self, page: int | None = None) -> list[tuple[str, str]]:
        """Render to an ordered list of ``(key, value)`` pairs.

        Values are *not* URL-encoded here; that is the caller's job (see
        :func:`kusyllabus.encoding.build_query`).
        """
        params: list[tuple[str, str]] = []

        def _opt(key: str, value: object) -> None:
            if value is None:
                params.append((key, ""))
            elif isinstance(value, bool):
                params.append((key, "true" if value else "false"))
            else:
                params.append((key, str(value)))

        _opt("condition.departmentNo", _coerce_int(self.department_no))
        _opt("condition.openSyllabusTitle", self.open_syllabus_title)
        _opt("condition.openSyllabusTitleEn", self.open_syllabus_title_en)
        _opt("condition.courseNumberingJugyokeitaiNo", _coerce_int(self.jugyokeitai_no))
        _opt("condition.courseNumberingLanguageNo", _coerce_int(self.language_no))
        _opt("condition.semesterNo", _coerce_int(self.semester_no))
        _opt("condition.courseNumberingLevelNo", _coerce_int(self.level_no))
        _opt("condition.courseNumberingBunkaNo", self.bunka_no)
        _opt("condition.teacherName", self.teacher_name)
        _opt("condition.teacherNameEn", self.teacher_name_en)
        _opt("condition.keyword", self.keyword)
        _opt("condition.keywordEn", self.keyword_en)
        _opt("condition.syutyu", self.syutyu)

        for xy in sorted(self.week_schedule):
            params.append((f"condition.weekSchedule[{xy}]", "true"))

        if page is not None:
            if page < 1:
                raise ValueError("page must be >= 1 (server returns 500 for page<=0)")
            params.append(("page", str(page)))
        return params


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(value)  # type: ignore[arg-type]
