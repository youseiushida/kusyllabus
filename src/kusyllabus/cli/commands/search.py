"""``kusyllabus search`` subcommands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kusyllabus import KuSyllabusClient, SearchCondition
from kusyllabus.cli._common import emit_human, emit_json, error, get_options, info
from kusyllabus.cli._deliver import deliver
from kusyllabus.cli._errors import reject_enum, reject_pagination
from kusyllabus.cli._profile import ProfileStore
from kusyllabus.enums import (
    BUNKA_NAMES_JP,
    DayOfWeek,
    DepartmentNo,
    JugyokeitaiNo,
    LanguageNo,
    LevelNo,
    SemesterNo,
    week_schedule_index,
)

app = typer.Typer(help="Search syllabi. Wraps `/external/open_syllabus/search`.")


def _condition_from(
    *,
    profile: str | None,
    department: int | None,
    open_title: str | None,
    open_title_en: str | None,
    jugyokeitai: int | None,
    language: int | None,
    semester: int | None,
    level: int | None,
    bunka: int | None,
    teacher: str | None,
    teacher_en: str | None,
    keyword: str | None,
    keyword_en: str | None,
    syutyu: bool | None,
    slots: list[str],
) -> tuple[SearchCondition, str | None]:
    """Resolve flag values against the named profile (precedence: flag > profile)."""
    display_lang: str | None = None

    base = SearchCondition()
    profile_name = profile or get_options().profile
    if profile_name:
        store = ProfileStore()
        prof = store.get(profile_name)
        if prof is None:
            available = ", ".join(store.list_names()) or "(none saved)"
            error(
                f"--profile '{profile_name}' not found. Available: {available}",
                exit_code=2,
            )
            return base, display_lang  # unreachable; appease type checker
        base = SearchCondition(
            department_no=prof.department_no,
            open_syllabus_title=prof.open_syllabus_title,
            open_syllabus_title_en=prof.open_syllabus_title_en,
            jugyokeitai_no=prof.jugyokeitai_no,
            language_no=prof.language_no,
            semester_no=prof.semester_no,
            level_no=prof.level_no,
            bunka_no=prof.bunka_no,
            teacher_name=prof.teacher_name,
            teacher_name_en=prof.teacher_name_en,
            keyword=prof.keyword,
            keyword_en=prof.keyword_en,
            syutyu=bool(prof.syutyu) if prof.syutyu is not None else False,
            week_schedule=set(prof.week_schedule),
        )
        display_lang = prof.display_lang

    def _coerce(flag: str, value: int | None, enum_cls: type) -> int | None:
        if value is None:
            return None
        try:
            enum_cls(value)
        except ValueError:
            valid = [int(m) for m in enum_cls]
            reject_enum(flag, value, valid)
        return value

    if department is not None:
        base.department_no = _coerce("--department", department, DepartmentNo)
    if open_title is not None:
        base.open_syllabus_title = open_title
    if open_title_en is not None:
        base.open_syllabus_title_en = open_title_en
    if jugyokeitai is not None:
        base.jugyokeitai_no = _coerce("--class-style", jugyokeitai, JugyokeitaiNo)
    if language is not None:
        base.language_no = _coerce("--language", language, LanguageNo)
    if semester is not None:
        base.semester_no = _coerce("--semester", semester, SemesterNo)
    if level is not None:
        base.level_no = _coerce("--level", level, LevelNo)
    if bunka is not None:
        if bunka not in BUNKA_NAMES_JP:
            reject_enum("--bunka", bunka, sorted(BUNKA_NAMES_JP.keys()))
        base.bunka_no = bunka
    if teacher is not None:
        base.teacher_name = teacher
    if teacher_en is not None:
        base.teacher_name_en = teacher_en
    if keyword is not None:
        base.keyword = keyword
    if keyword_en is not None:
        base.keyword_en = keyword_en
    if syutyu is not None:
        base.syutyu = syutyu

    for slot in slots:
        d, p = _parse_slot(slot)
        base.week_schedule.add(week_schedule_index(d, p))
    return base, display_lang


def _parse_slot(slot: str) -> tuple[DayOfWeek, int]:
    """Parse ``mon1`` / ``wed.3`` / ``31`` into ``(DayOfWeek, period)``."""
    s = slot.strip().lower().replace(".", "")
    aliases = {
        "mon": DayOfWeek.MONDAY,
        "tue": DayOfWeek.TUESDAY,
        "wed": DayOfWeek.WEDNESDAY,
        "thu": DayOfWeek.THURSDAY,
        "fri": DayOfWeek.FRIDAY,
        "sat": DayOfWeek.SATURDAY,
        "sun": DayOfWeek.SUNDAY,
        "月": DayOfWeek.MONDAY,
        "火": DayOfWeek.TUESDAY,
        "水": DayOfWeek.WEDNESDAY,
        "木": DayOfWeek.THURSDAY,
        "金": DayOfWeek.FRIDAY,
        "土": DayOfWeek.SATURDAY,
        "日": DayOfWeek.SUNDAY,
    }
    for prefix, day in aliases.items():
        if s.startswith(prefix) and s[len(prefix) :].isdigit():
            return day, int(s[len(prefix) :])
    if s.isdigit() and len(s) == 2:
        # XY shorthand: 31 = Wed period 1
        return DayOfWeek(int(s[0])), int(s[1])
    valid = "mon1..fri5, sat1..sat4, 11..75, or kanji like 水1"
    reject_enum("--slot", slot, [valid])


@app.command("list")
def list_(
    department: Annotated[
        int | None,
        typer.Option(
            "--department", "-d", help="Department code (see `kusyllabus master departments`)."
        ),
    ] = None,
    open_title: Annotated[
        str | None, typer.Option("--open-title", help="Academic-area filter (JP).")
    ] = None,
    open_title_en: Annotated[
        str | None, typer.Option("--open-title-en", help="Academic-area filter (EN).")
    ] = None,
    jugyokeitai: Annotated[
        int | None, typer.Option("--class-style", help="Class style code 1..7.")
    ] = None,
    language: Annotated[
        int | None, typer.Option("--language", help="Language code 1..4 (1=JA, 2=EN).")
    ] = None,
    semester: Annotated[
        int | None, typer.Option("--semester", help="Semester code (1..13, 17).")
    ] = None,
    level: Annotated[int | None, typer.Option("--level", help="Level code 1..9.")] = None,
    bunka: Annotated[int | None, typer.Option("--bunka", help="Academic field code 1..86.")] = None,
    teacher: Annotated[
        str | None, typer.Option("--teacher", help="Instructor name substring (JP).")
    ] = None,
    teacher_en: Annotated[
        str | None, typer.Option("--teacher-en", help="Instructor name substring (EN).")
    ] = None,
    keyword: Annotated[
        str | None, typer.Option("--keyword", "-k", help="Keyword substring (JP).")
    ] = None,
    keyword_en: Annotated[
        str | None, typer.Option("--keyword-en", help="Keyword substring (EN).")
    ] = None,
    syutyu: Annotated[
        bool | None,
        typer.Option("--intensive/--no-intensive", help="Filter to intensive courses only."),
    ] = None,
    slot: Annotated[
        list[str] | None,
        typer.Option(
            "--slot", help="Day-period slot like 'wed1' or '水1'. Repeatable; combined as OR."
        ),
    ] = None,
    page: Annotated[
        int, typer.Option("--page", help="Page number (1-based; <=0 returns HTTP 500 upstream).")
    ] = 1,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit", help="Stop after N rows total (across pages). Default: one page (10)."
        ),
    ] = None,
    profile: Annotated[
        str | None, typer.Option("--profile", help="Named profile to apply.")
    ] = None,
    display_lang: Annotated[
        str | None, typer.Option("--lang", help="Display language: 'ja' or 'en'.")
    ] = None,
    deliver_to: Annotated[
        str | None,
        typer.Option(
            "--deliver",
            help="Where to send the JSON result: stdout (default), file:<path>, webhook:<url>.",
        ),
    ] = None,
) -> None:
    """List matching syllabi. Use ``--limit`` to keep responses bounded."""
    if page < 1:
        reject_pagination(page)

    condition, profile_lang = _condition_from(
        profile=profile,
        department=department,
        open_title=open_title,
        open_title_en=open_title_en,
        jugyokeitai=jugyokeitai,
        language=language,
        semester=semester,
        level=level,
        bunka=bunka,
        teacher=teacher,
        teacher_en=teacher_en,
        keyword=keyword,
        keyword_en=keyword_en,
        syutyu=syutyu,
        slots=slot or [],
    )
    final_lang = display_lang or profile_lang

    rows = []
    total = 0
    truncated = False
    with KuSyllabusClient() as ku:
        result = ku.search(condition, page=page, display_lang=final_lang)
        total = result.total
        rows.extend(result.rows)
        if limit is not None:
            while len(rows) < limit and result.has_next_page:
                page += 1
                info(f"fetching page {page} (have {len(rows)} of {total})")
                result = ku.search(condition, page=page, display_lang=final_lang)
                rows.extend(result.rows)
            if len(rows) > limit:
                truncated = True
                rows = rows[:limit]

    payload = {
        "total": total,
        "page": page,
        "page_size": 10,
        "rows_returned": len(rows),
        "rows": [r.model_dump(mode="json") for r in rows],
        "truncated": truncated,
        "hint": (
            "results truncated by --limit; raise --limit or add filters to narrow"
            if truncated
            else None
        ),
        "next_page": page + 1 if (limit is None and rows and total > page * 10) else None,
    }

    if deliver_to:
        result = deliver(payload, deliver_to)
        if not get_options().json:
            emit_human(result)
        else:
            emit_json(result)
        return

    if get_options().json:
        emit_json(payload)
        return

    table = Table(title=f"{total} match(es) — showing {len(rows)}", show_lines=False, box=None)
    for col in ("lectureNo", "title", "instructors", "dept", "slot", "lang", "semester", "level"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r.lecture_no),
            r.title,
            "\n".join(r.instructors),
            r.department,
            "\n".join(r.days_and_periods),
            r.language,
            r.semester,
            r.level,
        )
    emit_human(table)
    if truncated:
        info("results truncated by --limit")


@app.command("count")
def count(
    department: Annotated[int | None, typer.Option("--department", "-d")] = None,
    keyword: Annotated[str | None, typer.Option("--keyword", "-k")] = None,
    slot: Annotated[list[str] | None, typer.Option("--slot")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
) -> None:
    """Return only the result count (1 lightweight request)."""
    condition, _ = _condition_from(
        profile=profile,
        department=department,
        open_title=None,
        open_title_en=None,
        jugyokeitai=None,
        language=None,
        semester=None,
        level=None,
        bunka=None,
        teacher=None,
        teacher_en=None,
        keyword=keyword,
        keyword_en=None,
        syutyu=None,
        slots=slot or [],
    )
    with KuSyllabusClient() as ku:
        result = ku.search(condition, page=1)
    payload = {"total": result.total, "page_count": result.page_count}
    if get_options().json:
        emit_json(payload)
    else:
        emit_human(f"{result.total} matching slot(s) across {result.page_count} page(s)")
