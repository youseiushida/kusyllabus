"""``kusyllabus master`` — surface the static enums for agent discovery."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kusyllabus.cli._common import emit_human, emit_json, get_options
from kusyllabus.cli._errors import reject_enum
from kusyllabus.enums import (
    BUNKA_NAMES_EN,
    BUNKA_NAMES_JP,
    DayOfWeek,
    DepartmentNo,
    JugyokeitaiNo,
    LanguageNo,
    LevelNo,
    SemesterNo,
)

app = typer.Typer(help="Inspect master enums (departments, semesters, levels, ...).")


_ENUMS = {
    "departments": DepartmentNo,
    "class-style": JugyokeitaiNo,
    "language": LanguageNo,
    "semester": SemesterNo,
    "level": LevelNo,
    "day": DayOfWeek,
}


def _emit_enum(name: str, enum_cls: type) -> None:
    rows = [
        {"value": int(m), "name": m.name, "label_jp": m.label_jp, "label_en": m.label_en}
        for m in enum_cls
    ]
    if get_options().json:
        emit_json({"enum": name, "members": rows})
        return
    table = Table(title=name)
    for col in ("value", "name", "JP", "EN"):
        table.add_column(col)
    for r in rows:
        table.add_row(str(r["value"]), r["name"], r["label_jp"], r["label_en"])
    emit_human(table)


@app.command("list")
def list_() -> None:
    """List every available master category name."""
    names = [*sorted(_ENUMS), "bunka"]
    if get_options().json:
        emit_json({"masters": names})
        return
    for n in names:
        emit_human(n)


for _cmd_name in _ENUMS:

    def _make_cmd(cmd_name: str, enum_cls: type):
        @app.command(cmd_name, help=f"Show the {cmd_name} master enum.")
        def _show() -> None:
            _emit_enum(cmd_name, enum_cls)

        return _show

    _make_cmd(_cmd_name, _ENUMS[_cmd_name])


@app.command("bunka")
def bunka(
    value: Annotated[
        int | None, typer.Option("--value", "-v", help="Look up a single bunkaNo (1..86).")
    ] = None,
) -> None:
    """Show the 86-item academic-field master (`courseNumberingBunkaNo`)."""
    if value is not None:
        if value not in BUNKA_NAMES_JP:
            reject_enum("--value", value, sorted(BUNKA_NAMES_JP.keys()))
        payload = {
            "value": value,
            "label_jp": BUNKA_NAMES_JP[value],
            "label_en": BUNKA_NAMES_EN[value],
        }
        if get_options().json:
            emit_json(payload)
        else:
            emit_human(f"{value}: {payload['label_jp']} / {payload['label_en']}")
        return

    rows = [
        {"value": v, "label_jp": BUNKA_NAMES_JP[v], "label_en": BUNKA_NAMES_EN.get(v, "")}
        for v in sorted(BUNKA_NAMES_JP)
    ]
    if get_options().json:
        emit_json({"enum": "bunka", "members": rows})
        return
    table = Table(title="bunka")
    for col in ("value", "JP", "EN"):
        table.add_column(col)
    for r in rows:
        table.add_row(str(r["value"]), r["label_jp"], r["label_en"])
    emit_human(table)
