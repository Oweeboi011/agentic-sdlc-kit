"""Runtime file formats (GitHub Copilot, Claude Code). Format changes stay in this module (plan R-04).

Pinned 2026-11-10 from docs.github.com custom-agents-configuration, add-skills, custom-instructions-support,
and code.claude.com sub-agents, skills, memory.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from kit_sync.kit import Doc, Kit

CLAUDE_TOOLS = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "Write"],
    "execute": ["Bash"],
    "todo": ["TodoWrite"],
    "web": ["WebFetch", "WebSearch"],
    "agent": ["Agent"],
}
COPILOT_BUILTIN_MCP = frozenset({"github", "playwright"})
_SECRET = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")


class _Dumper(yaml.SafeDumper):
    """Block mappings, inline lists of scalars: the shape both runtimes document."""


def _list(dumper: yaml.SafeDumper, items: list[Any]) -> yaml.Node:
    flow = all(not isinstance(i, (dict, list)) for i in items)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", items, flow_style=flow)


_Dumper.add_representer(list, _list)


def with_frontmatter(meta: dict[str, Any], body: str) -> str:
    dumped = yaml.dump(meta, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{dumped}---\n{body.lstrip(chr(10))}"


def _footer(agent: Doc) -> str:
    gate = agent.meta["human_gate"]
    lines = [
        "",
        "## Kit rules",
        "",
        f"- Propose only: comment or open a draft PR. The {gate['reviewer']} confirms before anything takes "
        "effect; never merge, deploy or approve.",
    ]
    if agent.meta.get("skills"):
        lines.append(f"- Skills: {', '.join(f'`{s}`' for s in agent.meta['skills'])}.")
    return "\n".join(lines) + "\n"


def _body(agent: Doc) -> str:
    return agent.body.rstrip("\n") + "\n" + _footer(agent)


def _copilot_server(server: dict[str, Any]) -> dict[str, Any]:
    """`${NAME}` in url, env and headers become Copilot secrets, which need the COPILOT_MCP_ prefix."""

    def secret(value: str) -> str:
        return _SECRET.sub(r"${{ secrets.COPILOT_MCP_\1 }}", value)

    out = dict(server)
    if "url" in out:
        out["url"] = secret(out["url"])
    for key in ("env", "headers"):
        if key in out:
            out[key] = {k: secret(v) for k, v in out[key].items()}
    return out


def copilot_agent(agent: Doc, kit: Kit) -> tuple[str, str]:
    servers = agent.meta.get("mcp", [])
    meta: dict[str, Any] = {
        "name": agent.name,
        "description": agent.meta["description"],
        "tools": [*agent.meta["tools"], *(f"{m}/*" for m in servers)],
    }
    custom = {m: _copilot_server(kit.mcp[m]) for m in servers if m not in COPILOT_BUILTIN_MCP}
    if custom:
        meta["mcp-servers"] = custom
    return f".github/agents/{agent.name}.agent.md", with_frontmatter(meta, _body(agent))


def _claude_server(server: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in server.items() if k != "tools"}  # `tools` is a Copilot-only key


def claude_agent(agent: Doc, kit: Kit) -> tuple[str, str]:
    meta: dict[str, Any] = {
        "name": agent.name,
        "description": agent.meta["description"],
        "tools": ", ".join(t for group in agent.meta["tools"] for t in CLAUDE_TOOLS[group]),
    }
    if agent.meta.get("skills"):
        meta["skills"] = list(agent.meta["skills"])
    if agent.meta.get("mcp"):
        meta["mcpServers"] = [{m: _claude_server(kit.mcp[m])} for m in agent.meta["mcp"]]
    return f".claude/agents/{agent.name}.md", with_frontmatter(meta, _body(agent))


def skill(doc: Doc, base: str) -> tuple[str, str]:
    meta = {"name": doc.name, "description": doc.meta["description"]}
    return f"{base}/{doc.name}/SKILL.md", with_frontmatter(meta, doc.body)


def instruction(doc: Doc) -> tuple[str, str]:
    path = f".github/instructions/{doc.name}.instructions.md"
    return path, with_frontmatter({"applyTo": doc.meta["applyTo"]}, doc.body)


def agents_md(instructions: list[Doc], gate: str) -> str:
    lines = [
        "# Agent rules",
        "",
        "Rendered from the agentic-sdlc-kit. Copilot reads this file; Claude Code imports it.",
        "",
        "- Agents propose; humans decide. Comment or open draft PRs; never merge, deploy or approve.",
        f"- Before handing off, run the project gate: `{gate}`.",
    ]
    if instructions:
        lines += ["- Path rules (read the file before editing a match):"]
        lines += [
            f"  - `{d.meta['applyTo']}`: `.github/instructions/{d.name}.instructions.md`"
            for d in instructions
        ]
    return "\n".join(lines) + "\n"


def claude_md(instructions: list[Doc]) -> str:
    imports = ["@../AGENTS.md"]
    imports += [
        f"@../.github/instructions/{d.name}.instructions.md"
        for d in instructions
        if d.meta["applyTo"] == "**"
    ]
    return "\n".join(imports) + "\n"
