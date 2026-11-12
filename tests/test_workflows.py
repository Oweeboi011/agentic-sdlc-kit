"""Reusable workflows (K5): callable only, documented inputs, values reach scripts via env, propose-only."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
AGENT_WORKFLOWS = ["claude-code", "planner"]
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


@pytest.mark.parametrize("name", AGENT_WORKFLOWS)
def test_agents_cannot_merge_review_or_mark_ready(name):
    text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
    assert "anthropics/claude-code-action@" in text
    if name == "planner":
        assert "--allowedTools" in text and "Edit" not in text
        return
    denied = re.search(r"denied='([^']+)'", text)
    assert denied, "claude-code must set a deny list"
    for command in REVIEW_COMMANDS:
        assert f"Bash({command}:*)" in denied[1]
    assert "Guard" in text and 'gh pr ready "$number" --undo' in text


def test_kit_ci_runs_its_own_reusable_workflows():
    jobs = load("ci")["jobs"]
    assert jobs["python"]["uses"] == "./.github/workflows/ci-python.yml"
    assert jobs["security"]["uses"] == "./.github/workflows/security.yml"


def test_readme_documents_every_reusable_workflow():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in REUSABLE:
        assert f"`{name}`" in readme, name
