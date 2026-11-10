"""Find kit content both in a source checkout (repo root) and in an installed wheel (inside the package)."""

from __future__ import annotations

from pathlib import Path

PACKAGE = Path(__file__).resolve().parent


def kit_dir(name: str) -> Path:
    installed = PACKAGE / name
    return installed if installed.is_dir() else PACKAGE.parent / name
