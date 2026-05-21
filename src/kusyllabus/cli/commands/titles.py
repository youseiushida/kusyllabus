"""``kusyllabus titles`` — academic-area dropdown values per department."""

from __future__ import annotations

from typing import Annotated

import typer

from kusyllabus import KuSyllabusClient
from kusyllabus.cli._common import emit_human, emit_json, get_options
from kusyllabus.cli._errors import reject_enum
from kusyllabus.enums import DepartmentNo

app = typer.Typer(help="Per-department academic-area (`openSyllabusTitle`) values.")


@app.command("list")
def list_(
    department: Annotated[
        int,
        typer.Option(
            "--department", "-d", help="Department code (`kusyllabus master departments`)."
        ),
    ],
) -> None:
    """Fetch the option list for ``condition.openSyllabusTitle``."""
    try:
        DepartmentNo(department)
    except ValueError:
        reject_enum("--department", department, [int(m) for m in DepartmentNo])
    with KuSyllabusClient() as ku:
        options = ku.get_syllabus_titles(department)
    payload = {
        "department_no": department,
        "count": len(options),
        "options": [o.model_dump(mode="json") for o in options],
    }
    if get_options().json:
        emit_json(payload)
        return
    if not options:
        emit_human("(no options)")
        return
    for o in options:
        emit_human(o.value)
