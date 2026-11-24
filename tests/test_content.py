"""The kit's own content: valid, renders for every runtime and stack, and stays propose-only."""

import json
from pathlib import Path

import yaml

from kit_sync.kit import Kit, load_kit
from kit_sync.layouts import copilot_agent
from kit_sync.paths import KIT_ROOT
from kit_sync.render import render
from kit_sync.validate import split_frontmatter, validate_kit

KIT = load_kit(KIT_ROOT)
EVERYTHING = {
    "kit": "v0",
    "runtimes": ["copilot", "claude-code"],
    "stack": ["python", "typescript-react", "bicep", "docker"],
    "gate": "make check",
    "agents": sorted(KIT.agents),
}


def test_kit_content_is_valid():
    assert validate_kit(KIT_ROOT) == []


def test_v01_content_counts():
    assert len(KIT.agents) == 7
    assert len(KIT.skills) == 10
    assert len(KIT.instructions) == 5
    assert sorted(KIT.mcp) == ["astral", "azure", "github", "playwright"]


def test_one_agent_per_stage_with_an_agent():
    assert sorted(a.meta["stage"] for a in KIT.agents.values()) == [1, 2, 3, 4, 5, 6, 8]


def test_every_agent_declares_evidence_with_a_kit_label():
    policy = json.loads((KIT_ROOT / "policies/labels.json").read_text(encoding="utf-8"))
    labels = {label["name"] for label in policy}
    kinds = {}
    for name, agent in KIT.agents.items():
        evidence = agent.meta["evidence"]
        assert evidence["label"] in labels, name
        assert evidence["trigger"] in agent.meta["triggers"], name
        kinds[name] = evidence["kind"]
    assert kinds == {
        "planner": "issue_comment",
        "coding": "pr",
        "review": "pr_comment",
        "test": "pr",
        "release": "release",
        "sre": "issue_comment",
        "feedback": "issue",
    }


def test_every_skill_is_used_by_an_agent():
    used = {s for a in KIT.agents.values() for s in a.meta.get("skills", [])}
    assert used == set(KIT.skills)


def test_mcp_servers_are_read_only_and_pinned():
    github, azure = KIT.mcp["github"], KIT.mcp["azure"]
    assert github["env"]["GITHUB_READ_ONLY"] == "1"
    assert "--read-only" in azure["args"]
    for server in KIT.mcp.values():
        args = server.get("args", [])
        assert not any(arg.endswith("@latest") or arg.endswith(":latest") for arg in args)
    astral = KIT.mcp["astral"]  # ASTRAL MCP: read-only tools only, URL and key from secrets
    assert astral["type"] == "http" and astral["url"] == "${ASTRAL_MCP_URL}"
    assert astral["headers"] == {"X-API-Key": "${ASTRAL_MCP_KEY}"}


def test_everything_renders_with_parseable_frontmatter():
    files = render(KIT, EVERYTHING)
    assert len([p for p in files if p.startswith(".github/agents/")]) == 7
    assert len([p for p in files if p.startswith(".claude/skills/")]) == 10
    for path, text in files.items():
        if text.startswith("---\n"):
            meta, _ = split_frontmatter(text)
            assert meta, path


def test_copilot_uses_builtin_github_and_maps_secrets_for_custom_servers():
    _, sre = copilot_agent(KIT.agents["sre"], KIT)
    meta, _ = split_frontmatter(sre)
    assert "github/*" in meta["tools"]
    assert list(meta["mcp-servers"]) == ["azure", "astral"]
    astral = meta["mcp-servers"]["astral"]
    assert astral["url"] == "${{ secrets.COPILOT_MCP_ASTRAL_MCP_URL }}"
    assert astral["headers"]["X-API-Key"] == "${{ secrets.COPILOT_MCP_ASTRAL_MCP_KEY }}"
    servers = {**KIT.mcp, "azure": {"env": {"T": "${TOKEN}"}}}
    custom = Kit(KIT.agents, KIT.skills, KIT.instructions, servers)
    meta, _ = split_frontmatter(copilot_agent(KIT.agents["sre"], custom)[1])
    assert meta["mcp-servers"]["azure"]["env"]["T"] == "${{ secrets.COPILOT_MCP_TOKEN }}"


def test_wheel_package_data_covers_all_content():
    pyproject = (KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for folder in ("schemas", "agents", "skills", "instructions", "mcp", "templates", "policies", "presets"):
        assert f'"kit_sync.{folder}" = "{folder}"' in pyproject
        assert (KIT_ROOT / folder).is_dir()


def test_skill_frontmatter_is_plain_yaml():
    for path in Path(KIT_ROOT, "skills").glob("*/SKILL.md"):
        meta = yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
        assert set(meta) == {"name", "description"}
