"""Reusable workflows (K5): callable only, documented inputs, values reach scripts via env, propose-only."""

import re
from pathlib import Path

import pytest
import yaml

from kit_sync.kit import load_kit
from kit_sync.paths import KIT_ROOT

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
# Reusable agent workflow -> the kit agent it runs.
AGENT_WORKFLOWS = {
    "claude-code": "coding",
    "feedback": "feedback",
    "planner": "planner",
    "release-agent": "release",
    "review": "review",
    "sre": "sre",
    "test": "test",
}
COMMENT_AGENTS = ["feedback", "planner", "review", "sre"]
PR_AGENTS = ["claude-code", "test"]
EVIDENCE = "ava-innersource/agentic-sdlc-kit/.github/actions/agent-evidence@v0"
ACTION = ROOT / ".github" / "actions" / "agent-evidence" / "action.yml"
STARTER = ROOT / "templates" / "starters" / "github" / "workflows" / "agents.yml"
REUSABLE = [
    "ci-node",
    "ci-python",
    "deploy-aca",
    "e2e-playwright",
    "iac-validate",
    "kit-drift",
    "security",
    *AGENT_WORKFLOWS,
]
REVIEW_COMMANDS = ("gh pr merge", "gh pr review", "gh pr ready")
INPUT_REF = re.compile(r"\binputs\.([a-z0-9-]+)")


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8"))


def triggers(workflow: dict) -> dict:
    return workflow["on"] if "on" in workflow else workflow[True]  # PyYAML reads `on` as True


def steps(workflow: dict):
    for job in workflow["jobs"].values():
        yield from job.get("steps", [])


@pytest.mark.parametrize("name", REUSABLE)
def test_reusable_workflow_is_only_callable(name):
    assert list(triggers(load(name))) == ["workflow_call"]


@pytest.mark.parametrize("name", REUSABLE)
def test_inputs_are_typed_documented_and_used(name):
    text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
    inputs = triggers(load(name))["workflow_call"].get("inputs", {})
    for key, spec in inputs.items():
        assert spec.get("description"), key
        assert spec["type"] in {"string", "number", "boolean"}, key
        assert not (spec.get("required") and "default" in spec), key
    used = set(INPUT_REF.findall(text))  # `if:` conditions reference inputs without ${{ }}
    assert used == set(inputs)


@pytest.mark.parametrize("name", REUSABLE)
def test_scripts_take_values_through_env(name):
    for step in steps(load(name)):
        assert "${{" not in step.get("run", ""), step.get("name", step["run"][:40])


@pytest.mark.parametrize("name", REUSABLE)
def test_default_token_is_read_only(name):
    assert load(name)["permissions"]["contents"] == "read"


def test_actions_are_pinned():
    for path in WORKFLOWS.glob("*.yml"):
        for step in steps(yaml.safe_load(path.read_text(encoding="utf-8"))):
            uses = step.get("uses")
            if uses and not uses.startswith("./"):
                assert re.search(r"(@v\d+|@[0-9a-f]{40}|:\d+\.\d+\.\d+)$", uses), f"{path.name}: {uses}"


def test_no_workflow_merges_approves_or_runs_untrusted_code():
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "pull_request_target" not in text, path.name
        assert "--approve" not in text, path.name
        for step in steps(yaml.safe_load(text)):
            for line in step.get("run", "").splitlines():
                command = line.strip()
                # Turning a PR back into a draft (`--undo`) is the one review-state change allowed.
                if command.startswith(REVIEW_COMMANDS) and "--undo" not in command:
                    raise AssertionError(f"{path.name}: {command}")


@pytest.mark.parametrize("name", COMMENT_AGENTS)
def test_comment_agents_have_an_allow_list_and_no_edit_tools(name):
    text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
    assert "anthropics/claude-code-action@" in text
    assert "--allowedTools" in text and "Edit" not in text and "Write" not in text


@pytest.mark.parametrize("name", PR_AGENTS)
def test_pr_agents_cannot_merge_review_or_mark_ready(name):
    text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
    denied = re.search(r"denied='([^']+)'", text)
    assert denied, f"{name} must set a deny list"
    for command in REVIEW_COMMANDS:
        assert f"Bash({command}:*)" in denied[1]
    assert "Guard" in text and 'gh pr ready "$number" --undo' in text


def test_test_agent_may_only_change_test_files():
    text = (WORKFLOWS / "test.yml").read_text(encoding="utf-8")
    assert 'grep -Ev "$TEST_FILES"' in text
    pattern = re.compile(triggers(load("test"))["workflow_call"]["inputs"]["test-files"]["default"])
    tests = ["tests/test_app.py", "src/app.test.ts", "web/__tests__/x.tsx", "pkg/test_util.py", "conftest.py"]
    for path in tests:
        assert pattern.search(path), path
    for path in ["src/app.py", "src/latest.ts", "contest.py"]:
        assert not pattern.search(path), path


def test_release_agent_keeps_releases_draft():
    text = (WORKFLOWS / "release-agent.yml").read_text(encoding="utf-8")
    assert "--draft" in text and 'gh release edit "$tag" --draft=true' in text
    assert "git push" not in text and "gh release edit:" not in text


@pytest.mark.parametrize(("name", "agent"), AGENT_WORKFLOWS.items())
def test_every_agent_output_gets_the_evidence_marker(name, agent):
    spec = load_kit(KIT_ROOT).agents[agent].meta["evidence"]
    marks = [s for s in steps(load(name)) if s.get("uses") == EVIDENCE]
    assert len(marks) == 1, name
    step = marks[0]
    assert step["if"] == "always()"
    assert step["with"]["agent"] == agent
    assert step["with"]["kind"] == spec["kind"]
    assert step["with"]["label"] == spec["label"]
    assert step["with"]["since"] == "${{ steps.args.outputs.since }}"
    assert "since=$(date -u" in (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")


def test_evidence_action_takes_values_through_env_and_writes_the_marker():
    action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"
    for key, spec in action["inputs"].items():
        assert spec.get("description"), key
    for step in action["runs"]["steps"]:
        assert "${{" not in step["run"]
    script = action["runs"]["steps"][0]["run"]
    assert "<!-- agentic-sdlc-kit agent=$AGENT kit=$kit run=$GITHUB_RUN_ID model=" in script
    assert '.user.type == "Bot"' in script and "GITHUB_STEP_SUMMARY" in script


def test_starter_runs_every_agent_workflow():
    jobs = yaml.safe_load(STARTER.read_text(encoding="utf-8"))["jobs"]
    used = {job["uses"].split("/")[-1].removesuffix(".yml@v0") for job in jobs.values()}
    assert used == set(AGENT_WORKFLOWS)
    sample = ROOT / "examples" / "sample-project" / ".github" / "workflows" / "agents.yml"
    assert sample.read_text(encoding="utf-8") == STARTER.read_text(encoding="utf-8")


def test_kit_ci_runs_its_own_reusable_workflows():
    jobs = load("ci")["jobs"]
    assert jobs["python"]["uses"] == "./.github/workflows/ci-python.yml"
    assert jobs["security"]["uses"] == "./.github/workflows/security.yml"


def test_readme_documents_every_reusable_workflow():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in REUSABLE:
        assert f"`{name}`" in readme, name
