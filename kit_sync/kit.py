"""Load canonical kit content and a project's config. Run `validate` first; loading assumes valid input."""

from __future__ import annotations

import json
from dataclasses import dataclass
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


def _doc(path: Path, name: str) -> Doc:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return Doc(name, meta, body)


def load_kit(root: Path) -> Kit:
    return Kit(
        agents={p.stem: _doc(p, p.stem) for p in sorted((root / "agents").glob("*.md"))},
        skills={p.parent.name: _doc(p, p.parent.name) for p in sorted((root / "skills").glob("*/SKILL.md"))},
        instructions={p.stem: _doc(p, p.stem) for p in sorted((root / "instructions").glob("*.md"))},
        mcp={
            p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((root / "mcp").glob("*.json"))
        },
    )


def load_config(project: Path) -> dict[str, Any]:
    return yaml.safe_load((project / CONFIG).read_text(encoding="utf-8"))
