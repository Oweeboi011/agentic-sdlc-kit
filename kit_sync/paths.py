"""Find kit content in a source checkout (repo root) or an installed wheel (inside the package)."""

from __future__ import annotations

from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
KIT_ROOT = PACKAGE if (PACKAGE / "schemas").is_dir() else PACKAGE.parent


def kit_dir(name: str) -> Path:
    return KIT_ROOT / name
