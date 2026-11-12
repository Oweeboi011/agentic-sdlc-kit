"""Load canonical kit content and a project's config. Run `validate` first; loading assumes valid input."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kit_sync.validate import CONFIG, split_frontmatter


@dataclass(frozen=True)
class Doc:
    name: str
    meta: dict[str, Any]
    body: str


@dataclass(frozen=True)
class Kit:
    agents: dict[str, Doc]
    skills: dict[str, Doc]
    instructions: dict[str, Doc]
    mcp: dict[str, dict[str, Any]]
    templates: dict[str, str] = field(default_factory=dict)  # project path -> text (templates/managed)


def _doc(path: Path, name: str) -> Doc:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return Doc(name, meta, body)


def project_path(rel: str) -> str:
    """Kit folders drop the leading dot (`github/...` -> `.github/...`) so the wheel can package them."""
    return rel if rel.split("/", 1)[0] not in {"github", "githooks"} else f".{rel}"


def load_files(folder: Path) -> dict[str, str]:
    files = sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []
    return {project_path(p.relative_to(folder).as_posix()): p.read_text(encoding="utf-8") for p in files}


def load_kit(root: Path) -> Kit:
    return Kit(
        agents={p.stem: _doc(p, p.stem) for p in sorted((root / "agents").glob("*.md"))},
        skills={p.parent.name: _doc(p, p.parent.name) for p in sorted((root / "skills").glob("*/SKILL.md"))},
        instructions={p.stem: _doc(p, p.stem) for p in sorted((root / "instructions").glob("*.md"))},
        mcp={
            p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((root / "mcp").glob("*.json"))
        },
        templates=load_files(root / "templates" / "managed"),
    )


def load_config(project: Path) -> dict[str, Any]:
    return yaml.safe_load((project / CONFIG).read_text(encoding="utf-8"))
