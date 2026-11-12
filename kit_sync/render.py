"""Pick what to render for a project and render it to {relative path: content} (no marker yet)."""

from __future__ import annotations

from typing import Any

from kit_sync import layouts
from kit_sync.kit import Doc, Kit

# Template groups a project can turn off (`templates` in astral-kit.yml; default: all).
TEMPLATE_GROUPS = {
    "issue-forms": ".github/ISSUE_TEMPLATE/",
    "pr-template": ".github/pull_request_template.md",
    "githooks": ".githooks/",
}


def fill(text: str, config: dict[str, Any]) -> str:
    return text.replace("{{gate}}", config["gate"])


def _templates(kit: Kit, config: dict[str, Any]) -> list[tuple[str, str]]:
    prefixes = tuple(TEMPLATE_GROUPS[g] for g in config.get("templates", TEMPLATE_GROUPS))
    return [(rel, fill(text, config)) for rel, text in kit.templates.items() if rel.startswith(prefixes)]


def _instructions(kit: Kit, stack: set[str]) -> list[Doc]:
    return [d for d in kit.instructions.values() if not d.meta.get("stack") or stack & set(d.meta["stack"])]


def render(kit: Kit, config: dict[str, Any]) -> dict[str, str]:
    runtimes = set(config["runtimes"])
    agents = [kit.agents[name] for name in config["agents"]]
    skills = sorted({s for agent in agents for s in agent.meta.get("skills", [])})
    instructions = _instructions(kit, set(config["stack"]))

    files: list[tuple[str, str]] = []
    if "copilot" in runtimes:
        files += [layouts.copilot_agent(a, kit) for a in agents]
    if "claude-code" in runtimes:
        files += [layouts.claude_agent(a, kit) for a in agents]
    # Copilot also reads .claude/skills, so one copy serves both runtimes.
    skill_base = ".claude/skills" if "claude-code" in runtimes else ".github/skills"
    files += [layouts.skill(kit.skills[s], skill_base) for s in skills]
    files += [layouts.instruction(d) for d in instructions]
    files += _templates(kit, config)
    files.append(("AGENTS.md", layouts.agents_md(instructions, config["gate"])))
    if "claude-code" in runtimes:
        files.append((".claude/CLAUDE.md", layouts.claude_md(instructions)))
    return dict(sorted(files))
