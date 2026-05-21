"""Generate the machine-readable ``agent-context`` payload.

Rule 7 (three-layer introspection) calls for a versioned, machine-readable
description of the CLI's surface. We walk Typer's registered commands and
flatten parameters into a serialisable shape, then attach masters (enums)
and feature toggles so agents can self-discover everything in one call.
"""

from __future__ import annotations

import inspect
import os
from typing import Any, get_args, get_origin

import click
import typer
from typer.main import get_command

from kusyllabus.cli._feedback import ENDPOINT_ENV
from kusyllabus.cli._paths import feedback_path, jobs_path, profiles_path
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

SCHEMA_VERSION = "1"


def build_agent_context(app: typer.Typer, *, profiles: list[str]) -> dict[str, Any]:
    cli = get_command(app)
    ctx = click.Context(cli, info_name=cli.name)
    commands = _walk_command(cli, ctx, path=())
    return {
        "schema_version": SCHEMA_VERSION,
        "name": cli.name or "kusyllabus",
        "summary": (cli.help or "").strip().splitlines()[0] if cli.help else "",
        "commands": commands,
        "global_flags": _global_flags(cli),
        "masters": _masters(),
        "delivery_schemes": ["stdout", "file:<path>", "webhook:<url>"],
        "feedback": {
            "endpoint_env": ENDPOINT_ENV,
            "local_path": str(feedback_path()),
        },
        "state": {
            "profiles_path": str(profiles_path()),
            "jobs_path": str(jobs_path()),
        },
        "available_profiles": sorted(profiles),
    }


def _walk_command(
    cmd: click.Command,
    ctx: click.Context,
    *,
    path: tuple[str, ...],
) -> dict[str, Any]:
    info: dict[str, Any] = {
        "name": cmd.name,
        "summary": (cmd.help or "").strip().splitlines()[0] if cmd.help else "",
        "path": " ".join((*path, cmd.name or "")).strip(),
    }
    if isinstance(cmd, click.Group):
        info["subcommands"] = {}
        for sub_name in cmd.list_commands(ctx):
            sub_cmd = cmd.get_command(ctx, sub_name)
            if sub_cmd is None:
                continue
            info["subcommands"][sub_name] = _walk_command(
                sub_cmd, ctx, path=(*path, cmd.name or "")
            )
    else:
        info["flags"] = _describe_params(cmd)
    return info


def _describe_params(cmd: click.Command) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for param in cmd.params:
        if isinstance(param, click.Option):
            key = param.opts[0] if param.opts else param.name or ""
            out[key] = _describe_option(param)
        elif isinstance(param, click.Argument):
            out[param.name or ""] = {
                "type": _type_name(param.type),
                "required": param.required,
                "kind": "argument",
            }
    return out


def _describe_option(option: click.Option) -> dict[str, Any]:
    type_obj = option.type
    info: dict[str, Any] = {
        "type": _type_name(type_obj),
        "required": option.required,
        "default": option.default
        if option.default is not None and not callable(option.default)
        else None,
        "help": (option.help or "").strip(),
    }
    if isinstance(type_obj, click.Choice):
        info["values"] = list(type_obj.choices)
    if getattr(option, "is_flag", False):
        info["type"] = "bool"
    if option.envvar:
        info["envvar"] = option.envvar if isinstance(option.envvar, str) else list(option.envvar)
    return info


def _type_name(type_obj: Any) -> str:
    if isinstance(type_obj, click.types.StringParamType):
        return "string"
    if isinstance(type_obj, click.types.IntParamType):
        return "int"
    if isinstance(type_obj, click.types.FloatParamType):
        return "float"
    if isinstance(type_obj, click.types.BoolParamType):
        return "bool"
    if isinstance(type_obj, click.Choice):
        return "enum"
    return type_obj.__class__.__name__.replace("ParamType", "").lower() or "string"


def _global_flags(root: click.Command) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for param in root.params:
        if isinstance(param, click.Option):
            key = param.opts[0] if param.opts else param.name or ""
            out[key] = _describe_option(param)
    return out


def _masters() -> dict[str, dict[str, Any]]:
    return {
        "departments": _enum_dump(DepartmentNo),
        "jugyokeitai": _enum_dump(JugyokeitaiNo),
        "language": _enum_dump(LanguageNo),
        "semester": _enum_dump(SemesterNo),
        "level": _enum_dump(LevelNo),
        "day_of_week": _enum_dump(DayOfWeek),
        "bunka": {
            "labels_jp": BUNKA_NAMES_JP,
            "labels_en": BUNKA_NAMES_EN,
            "valid_range": [1, 86],
        },
    }


def _enum_dump(enum_cls: Any) -> dict[str, Any]:
    members = []
    for member in enum_cls:
        members.append(
            {
                "name": member.name,
                "value": int(member),
                "label_jp": getattr(member, "label_jp", None),
                "label_en": getattr(member, "label_en", None),
            }
        )
    return {"members": members}


def _suppress_unused_imports() -> None:
    _ = (inspect, get_args, get_origin, os)


__all__ = ["SCHEMA_VERSION", "build_agent_context"]
