"""Validate kit content (agents, skills) and a project's `.github/astral-kit.yml` against `schemas/`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from kit_sync.paths import kit_dir

CONFIG = Path(".github/astral-kit.yml")


@dataclass(frozen=True)
class Problem:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@cache
def _validator(kind: str) -> Draft202012Validator:
    schema = json.loads((kit_dir("schemas") / f"{kind}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter, body); frontmatter is the YAML mapping between the first two `---` lines."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter: the file must start with ---")
    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            data = yaml.safe_load("".join(lines[1:end])) or {}
            if not isinstance(data, dict):
                raise ValueError("frontmatter must be a YAML mapping")
            return data, "".join(lines[end + 1 :])
    raise ValueError("frontmatter is not closed: no second ---")


def schema_problems(kind: str, data: Any, where: str) -> list[Problem]:
    errors = sorted(_validator(kind).iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    return [Problem(where, f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}") for e in errors]


def _strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _load(path: Path, kind: str, where: str) -> tuple[dict[str, Any] | None, list[Problem]]:
    try:
        data, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        return None, [Problem(where, str(exc))]
    return data, schema_problems(kind, data, where)


def _name_matches(data: dict[str, Any], expected: str, where: str, of: str) -> list[Problem]:
    name = data.get("name")
    return [] if name == expected else [Problem(where, f"name {name!r} must match the {of} {expected!r}")]


def _mcp_problems(path: Path, where: str) -> list[Problem]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Problem(where, f"invalid JSON: {exc}")]
    return [] if isinstance(data, dict) else [Problem(where, "must be a JSON object (one server definition)")]


def kit_agents(kit: Path) -> set[str]:
    return {p.stem for p in (kit / "agents").glob("*.md")}


def validate_kit(kit: Path) -> list[Problem]:
    problems: list[Problem] = []
    skills: set[str] = set()
    for path in sorted((kit / "skills").glob("*/SKILL.md")):
        where = path.relative_to(kit).as_posix()
        skills.add(path.parent.name)
        data, found = _load(path, "skill", where)
        problems += found
        if data is not None:
            problems += _name_matches(data, path.parent.name, where, "folder")
    for path in sorted((kit / "instructions").glob("*.md")):
        problems += _load(path, "instruction", path.relative_to(kit).as_posix())[1]
    servers = {p.stem for p in (kit / "mcp").glob("*.json")}
    for name in sorted(servers):
        problems += _mcp_problems(kit / "mcp" / f"{name}.json", f"mcp/{name}.json")
    for path in sorted((kit / "agents").glob("*.md")):
        where = path.relative_to(kit).as_posix()
        data, found = _load(path, "agent", where)
        problems += found
        if data is None:
            continue
        problems += _name_matches(data, path.stem, where, "file name")
        problems += [
            Problem(where, f"skill {s!r} not found (skills/{s}/SKILL.md)")
            for s in _strings(data.get("skills"))
            if s not in skills
        ]
        problems += [
            Problem(where, f"MCP server {m!r} not found (mcp/{m}.json)")
            for m in _strings(data.get("mcp"))
            if m not in servers
        ]
    return problems


def validate_config(project: Path, kit: Path) -> list[Problem]:
    path, where = project / CONFIG, CONFIG.as_posix()
    if not path.is_file():
        return [Problem(where, "not found")]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [Problem(where, f"invalid YAML: {exc}")]
    problems = schema_problems("astral-kit", data, where)
    if isinstance(data, dict):
        known = kit_agents(kit)
        problems += [
            Problem(where, f"agents: {a!r} is not a kit agent (agents/{a}.md)")
            for a in _strings(data.get("agents"))
            if a not in known
        ]
    return problems
