"""``kusyllabus all`` subcommands — walk the /all tree."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.tree import Tree

from kusyllabus import KuSyllabusClient, flatten_all_leaves
from kusyllabus.cli._common import emit_human, emit_json, get_options
from kusyllabus.cli._deliver import deliver

app = typer.Typer(help="Walk the `/all` page (full Department→Title→Syllabus tree).")


@app.command("tree")
def tree_(
    department: Annotated[
        int | None, typer.Option("--department", "-d", help="Restrict to one department code.")
    ] = None,
    kind: Annotated[str, typer.Option("--kind", help="'open', 'department' or 'all'.")] = "all",
    display_lang: Annotated[str | None, typer.Option("--lang")] = None,
    deliver_to: Annotated[str | None, typer.Option("--deliver")] = None,
) -> None:
    """Fetch the 3-level tree (Department → Title → Syllabus)."""
    with KuSyllabusClient() as ku:
        tree = ku.get_all_tree(display_lang=display_lang)

    if department is not None:
        from kusyllabus.enums import DepartmentNo

        try:
            dept_label = DepartmentNo(department).label_jp
        except ValueError:
            dept_label = None
        tree = [
            d
            for d in tree
            if (dept_label is not None and d.name == dept_label)
            or (dept_label is None and d.name and str(department) in d.name)
        ]

    if kind != "all":
        wanted = "open_syllabus" if kind == "open" else "department_syllabus"
        for dept in tree:
            for title in dept.children:
                title.children = [leaf for leaf in title.children if leaf.kind == wanted]

    payload = [d.model_dump(mode="json") for d in tree]
    if deliver_to:
        result = deliver(payload, deliver_to)
        if get_options().json:
            emit_json(result)
        else:
            emit_human(result)
        return

    if get_options().json:
        emit_json(payload)
        return

    rich_tree = Tree("[bold]/all[/bold]")
    for dept in tree:
        dnode = rich_tree.add(
            f"[bold cyan]{dept.name}[/bold cyan] ({sum(len(t.children) for t in dept.children)} leaves)"
        )
        for title in dept.children:
            tnode = dnode.add(f"{title.name}")
            for leaf in title.children:
                marker = "★" if leaf.kind == "open_syllabus" else "·"
                tnode.add(
                    f"{marker} {leaf.name} [dim](lectureNo={leaf.lecture_no}{', dept=' + str(leaf.department_no) if leaf.department_no else ''})[/dim]"
                )
    emit_human(rich_tree)


@app.command("leaves")
def leaves(
    department: Annotated[int | None, typer.Option("--department", "-d")] = None,
    kind: Annotated[str, typer.Option("--kind", help="'open', 'department', or 'all'.")] = "all",
    limit: Annotated[int | None, typer.Option("--limit")] = None,
    display_lang: Annotated[str | None, typer.Option("--lang")] = None,
) -> None:
    """Flatten the /all tree to a list of leaves."""
    with KuSyllabusClient() as ku:
        tree = ku.get_all_tree(display_lang=display_lang)
    flat = flatten_all_leaves(tree)
    if department is not None:
        flat = [n for n in flat if n.department_no == department]
    if kind != "all":
        wanted = "open_syllabus" if kind == "open" else "department_syllabus"
        flat = [n for n in flat if n.kind == wanted]
    truncated = limit is not None and len(flat) > limit
    if truncated:
        flat = flat[: limit or 0]

    payload = {
        "rows_returned": len(flat),
        "truncated": truncated,
        "hint": "results truncated by --limit; raise --limit or add filters" if truncated else None,
        "leaves": [n.model_dump(mode="json") for n in flat],
    }
    if get_options().json:
        emit_json(payload)
        return
    for n in flat:
        marker = "★" if n.kind == "open_syllabus" else "·"
        emit_human(
            f"{marker} {n.lecture_no:>6}  {n.name}  [dim](dept={n.department_no or '-'})[/dim]"
        )
