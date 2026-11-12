from pathlib import Path

import pytest

from kit_sync.cli import main
from kit_sync.validate import split_frontmatter, validate_config, validate_kit

AGENT = """---
name: planner
description: Refines needs-refinement issues into ready stories.
stage: 1
triggers: [label:needs-refinement, manual]
skills: [story-refinement]
tools: [read, search]
mcp: [github]
permissions: {issues: write, contents: read}
human_gate: {mode: propose, reviewer: product owner}
evidence: {kind: issue_comment, label: "agent:planner", trigger: label:needs-refinement}
---
Refine the issue.
"""
SKILL = """---
name: story-refinement
description: Turns a rough issue into a story with acceptance criteria.
---
Steps.
"""
CONFIG = """kit: v0
runtimes: [copilot, claude-code]
stack: [python, typescript-react]
gate: python tools/harness.py ci
agents: [planner]
deploy: {target: azure-container-apps, environments: [dev, staging, prod]}
"""


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def kit(tmp_path: Path) -> Path:
    root = tmp_path / "kit"
    write(root, "agents/planner.md", AGENT)
    write(root, "skills/story-refinement/SKILL.md", SKILL)
    write(root, "mcp/github.json", "{}")
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    write(root, ".github/astral-kit.yml", CONFIG)
    return root


def messages(problems) -> str:
    return "\n".join(map(str, problems))


def test_valid_kit_and_config_have_no_problems(kit, project):
    assert validate_kit(kit) == []
    assert validate_config(project, kit) == []


def test_frontmatter_handles_crlf_and_returns_body():
    data, body = split_frontmatter("---\r\nname: x\r\n---\r\nbody\r\n")
    assert data == {"name": "x"}
    assert body == "body\r\n"


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("no frontmatter", "must start with ---"),
        ("---\nname: x\n", "not closed"),
        ("---\n- a\n---\n", "mapping"),
    ],
)
def test_frontmatter_errors(text, error):
    with pytest.raises(ValueError, match=error):
        split_frontmatter(text)


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("human_gate: {mode: propose,", "human_gate: {mode: autonomous,", "human_gate/mode"),
        ("stage: 1", "stage: 9", "stage"),
        ("tools: [read, search]", "tools: [read, shell]", "tools/1"),
        ("triggers: [label:needs-refinement, manual]", "triggers: [push]", "triggers/0"),
        ("permissions: {issues: write, contents: read}", "permissions: {issues: admin}", "issues"),
        ("stage: 1\n", "stage: 1\nmodel: gpt\n", "'model' was unexpected"),
    ],
)
def test_agent_schema_rejects_bad_fields(kit, old, new, expected):
    write(kit, "agents/planner.md", AGENT.replace(old, new))
    assert expected in messages(validate_kit(kit))


def test_evidence_must_answer_one_of_the_triggers(kit):
    wrong = AGENT.replace("trigger: label:needs-refinement", "trigger: label:incident")
    write(kit, "agents/planner.md", wrong)
    found = messages(validate_kit(kit))
    assert "evidence trigger 'label:incident' is not one of the agent's triggers" in found


def test_agent_name_must_match_file(kit):
    write(kit, "agents/other.md", AGENT)
    assert "agents/other.md: name 'planner' must match the file name 'other'" in messages(validate_kit(kit))


def test_agent_references_must_exist(kit):
    broken = AGENT.replace("[story-refinement]", "[missing]").replace("[github]", "[azure]")
    write(kit, "agents/planner.md", broken)
    found = messages(validate_kit(kit))
    assert "skill 'missing' not found" in found
    assert "MCP server 'azure' not found" in found


def test_skill_name_must_match_folder_and_spec(kit):
    write(kit, "skills/Bad_Name/SKILL.md", SKILL.replace("story-refinement", "Bad_Name"))
    found = messages(validate_kit(kit))
    assert "skills/Bad_Name/SKILL.md: name: 'Bad_Name' does not match" in found


def test_broken_yaml_is_a_problem_not_a_crash(kit):
    write(kit, "agents/planner.md", "---\nname: [\n---\n")
    assert "agents/planner.md" in messages(validate_kit(kit))


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("kit: v0", "kit: 0.1", "kit"),
        ("kit: v0", "kit: v0.1", "kit"),
        ("runtimes: [copilot, claude-code]", "runtimes: [cursor]", "runtimes/0"),
        ("agents: [planner]", "agents: [deployer]", "'deployer' is not a kit agent"),
        ("gate: python tools/harness.py ci\n", "", "'gate' is a required property"),
    ],
)
def test_config_problems(kit, project, old, new, expected):
    write(project, ".github/astral-kit.yml", CONFIG.replace(old, new))
    assert expected in messages(validate_config(project, kit))


def test_missing_config_is_reported(kit, tmp_path):
    assert messages(validate_config(tmp_path, kit)) == ".github/astral-kit.yml: not found"


def test_cli_validate_exit_codes(kit, project, capsys):
    assert main(["--validate", "--kit", str(kit), "--project", str(project)]) == 0
    assert capsys.readouterr().out.strip() == "valid"
    write(kit, "agents/planner.md", AGENT.replace("stage: 1", "stage: 0"))
    assert main(["--validate", "--kit", str(kit)]) == 1
    assert "1 problem(s)" in capsys.readouterr().out
