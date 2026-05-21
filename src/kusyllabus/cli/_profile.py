"""Profile system — save/load named bundles of search defaults.

Precedence (per Rule 9): explicit flag > env var > profile value > default.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kusyllabus.cli._paths import profiles_path


class Profile(BaseModel):
    """A named bundle of search defaults.

    All fields mirror ``SearchCondition`` so the CLI can hydrate it directly.
    Anything not set falls through to the next layer of precedence.
    """

    name: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    department_no: int | None = None
    open_syllabus_title: str | None = None
    open_syllabus_title_en: str | None = None
    jugyokeitai_no: int | None = None
    language_no: int | None = None
    semester_no: int | None = None
    level_no: int | None = None
    bunka_no: int | None = None
    teacher_name: str | None = None
    teacher_name_en: str | None = None
    keyword: str | None = None
    keyword_en: str | None = None
    syutyu: bool | None = None
    week_schedule: list[int] = Field(default_factory=list)
    display_lang: str | None = None


class ProfileStore:
    """File-backed profile collection.

    Stores everything in a single JSON file (``profiles.json``) under the
    platformdirs config directory. Each profile is keyed by name.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or profiles_path()

    # ----- IO -------------------------------------------------------------

    def _load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": "1", "profiles": {}}
        with self.path.open("rb") as f:
            return json.loads(f.read().decode("utf-8"))

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("wb") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        tmp.replace(self.path)

    # ----- API ------------------------------------------------------------

    def list_names(self) -> list[str]:
        return sorted(self._load_raw().get("profiles", {}).keys())

    def list_profiles(self) -> list[Profile]:
        raw = self._load_raw().get("profiles", {})
        return [Profile.model_validate(v) for v in raw.values()]

    def get(self, name: str) -> Profile | None:
        raw = self._load_raw().get("profiles", {})
        v = raw.get(name)
        if v is None:
            return None
        return Profile.model_validate(v)

    def save(self, profile: Profile) -> Profile:
        data = self._load_raw()
        profiles = data.setdefault("profiles", {})
        existing = profiles.get(profile.name)
        if existing:
            profile.created_at = existing.get("created_at", profile.created_at)
        profile.updated_at = datetime.now(UTC).isoformat()
        profiles[profile.name] = profile.model_dump(mode="json")
        self._save_raw(data)
        return profile

    def delete(self, name: str) -> bool:
        data = self._load_raw()
        profiles = data.setdefault("profiles", {})
        if name in profiles:
            del profiles[name]
            self._save_raw(data)
            return True
        return False
