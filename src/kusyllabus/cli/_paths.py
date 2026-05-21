"""Cross-platform paths for CLI state, using platformdirs."""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_DIRS = PlatformDirs("kusyllabus", "kusyllabus", roaming=False)


def config_dir() -> Path:
    p = Path(_DIRS.user_config_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_dir() -> Path:
    p = Path(_DIRS.user_state_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = Path(_DIRS.user_cache_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def profiles_path() -> Path:
    return config_dir() / "profiles.json"


def jobs_path() -> Path:
    return state_dir() / "jobs.jsonl"


def feedback_path() -> Path:
    return state_dir() / "feedback.jsonl"
