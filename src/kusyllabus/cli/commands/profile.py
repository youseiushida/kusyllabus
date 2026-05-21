"""``kusyllabus profile`` — save/use named search-condition bundles."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kusyllabus.cli._common import emit_human, emit_json, error, get_options
from kusyllabus.cli._profile import Profile, ProfileStore

app = typer.Typer(help="Saved bundles of default search parameters.")


@app.command("save")
def save(
    name: Annotated[str, typer.Argument(help="Profile name.")],
    department: Annotated[int | None, typer.Option("--department", "-d")] = None,
    keyword: Annotated[str | None, typer.Option("--keyword", "-k")] = None,
    keyword_en: Annotated[str | None, typer.Option("--keyword-en")] = None,
    teacher: Annotated[str | None, typer.Option("--teacher")] = None,
    teacher_en: Annotated[str | None, typer.Option("--teacher-en")] = None,
    language: Annotated[int | None, typer.Option("--language")] = None,
    semester: Annotated[int | None, typer.Option("--semester")] = None,
    level: Annotated[int | None, typer.Option("--level")] = None,
    bunka: Annotated[int | None, typer.Option("--bunka")] = None,
    jugyokeitai: Annotated[int | None, typer.Option("--class-style")] = None,
    open_title: Annotated[str | None, typer.Option("--open-title")] = None,
    open_title_en: Annotated[str | None, typer.Option("--open-title-en")] = None,
    syutyu: Annotated[bool | None, typer.Option("--intensive/--no-intensive")] = None,
    slot: Annotated[
        list[int] | None,
        typer.Option("--slot-index", help="weekSchedule[XY] integer (repeatable)."),
    ] = None,
    display_lang: Annotated[str | None, typer.Option("--lang")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite if a profile by this name exists.")
    ] = False,
) -> None:
    """Create or update a saved profile (idempotent; ``--force`` to overwrite)."""
    store = ProfileStore()
    existing = store.get(name)
    if existing and not force:
        error(
            f"profile {name!r} already exists (pass --force to overwrite). "
            f"available: {', '.join(store.list_names())}",
            exit_code=2,
        )

    profile = Profile(
        name=name,
        department_no=department,
        open_syllabus_title=open_title,
        open_syllabus_title_en=open_title_en,
        jugyokeitai_no=jugyokeitai,
        language_no=language,
        semester_no=semester,
        level_no=level,
        bunka_no=bunka,
        teacher_name=teacher,
        teacher_name_en=teacher_en,
        keyword=keyword,
        keyword_en=keyword_en,
        syutyu=syutyu,
        week_schedule=list(slot or []),
        display_lang=display_lang,
    )
    saved = store.save(profile)
    if get_options().json:
        emit_json({"saved": saved.model_dump(mode="json"), "existed": existing is not None})
    else:
        verb = "updated" if existing else "saved"
        emit_human(f"profile {verb}: {name}")


@app.command("list")
def list_() -> None:
    """List saved profile names."""
    store = ProfileStore()
    profiles = store.list_profiles()
    if get_options().json:
        emit_json({"profiles": [p.model_dump(mode="json") for p in profiles]})
        return
    if not profiles:
        emit_human("(no profiles saved)")
        return
    t = Table()
    for col in ("name", "department", "keyword", "language", "semester", "slots"):
        t.add_column(col)
    for p in profiles:
        t.add_row(
            p.name,
            str(p.department_no or "-"),
            (p.keyword or p.keyword_en or "-"),
            str(p.language_no or "-"),
            str(p.semester_no or "-"),
            ",".join(str(x) for x in p.week_schedule) or "-",
        )
    emit_human(t)


@app.command("show")
def show(
    name: Annotated[str, typer.Argument()],
) -> None:
    """Show one profile."""
    store = ProfileStore()
    p = store.get(name)
    if p is None:
        error(
            f"profile {name!r} not found. available: {', '.join(store.list_names()) or '(none)'}",
            exit_code=4,
        )
    if get_options().json:
        emit_json(p.model_dump(mode="json"))
    else:
        emit_human(p.model_dump(mode="json"))


@app.command("delete")
def delete(
    name: Annotated[str, typer.Argument()],
    force: Annotated[bool, typer.Option("--force", help="Required to actually delete.")] = False,
) -> None:
    """Delete a profile (requires ``--force`` to confirm)."""
    if not force:
        error("pass --force to confirm deletion", exit_code=2)
    store = ProfileStore()
    deleted = store.delete(name)
    if not deleted:
        error(f"profile {name!r} not found", exit_code=4)
    if get_options().json:
        emit_json({"deleted": name})
    else:
        emit_human(f"deleted profile: {name}")
