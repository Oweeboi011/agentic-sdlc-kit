"""Canary golden tasks and graders (ADR-0026): every task loads, graders pass good and fail bad outputs."""

import re

import pytest
import yaml

from kit_sync.canary import (
    grade_feedback,
    grade_planner,
    grade_pr,
    grade_review,
    grade_sre,
    load_tasks,
)
from kit_sync.paths import KIT_ROOT

TASKS = load_tasks(KIT_ROOT / "canary" / "tasks")
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "canary.yml"


def mark(agent: str, body: str, at: str = "2026-11-13T06:00:00Z") -> dict:
    marker = f"<!-- agentic-sdlc-kit agent={agent} kit=v0.1.0 run=9 model=default -->"
    return {"body": f"{body}\n\n{marker}", "created_at": at, "html_url": f"https://gh/{agent}"}


GOOD_PLAN = """**Goal:** Finance users download their invoices as CSV.

**Acceptance criteria:**
1. Given the billing page, when I click Export, a CSV downloads.
2. The CSV has date, number, amount and status columns.
3. 5000 invoices export in under 10 seconds.

**Out of scope:** PDF export.

**Test notes:** unit for the CSV writer, e2e for the button.

**Estimate:** M

**Open questions:** Which time zone for dates?
"""


def test_every_kit_agent_but_release_has_a_golden_task():
    assert sorted(TASKS) == ["coding", "feedback", "planner", "review", "sre", "test"]
    for task in TASKS.values():
        assert task["rubric"] and task["seed"] in {"issue", "pr", "alert", "feedback"}


def test_review_task_plants_the_bug_on_the_expected_line():
    task = TASKS["review"]
    lines = task["files"][task["expected"]["path"]].splitlines()
    assert "number * size" in lines[task["expected"]["line"] - 1]


def test_test_task_bug_changes_the_function():
    task = TASKS["test"]
    assert task["bug"]["canary/money.py"] != task["files"]["canary/money.py"]


def test_planner_grader():
    assert grade_planner(TASKS["planner"], [mark("planner", GOOD_PLAN)]).passed
    thin = GOOD_PLAN.replace("**Open questions:** Which time zone for dates?\n", "")
    result = grade_planner(TASKS["planner"], [mark("planner", thin)])
    assert not result.passed and result.reasons == ["missing section: open questions"]
    two = GOOD_PLAN.replace("3. 5000 invoices export in under 10 seconds.\n", "")
    assert "2 acceptance criteria" in grade_planner(TASKS["planner"], [mark("planner", two)]).reasons[0]
    assert not grade_planner(TASKS["planner"], [{"body": GOOD_PLAN, "created_at": "x"}]).passed


@pytest.mark.parametrize(
    ("body", "passed"),
    [
        ("**Verdict:** needs changes\n### High\n- `canary/pagination.py:3` skips page 1", True),
        ("**Verdict:** needs changes\n- **medium** canary/pagination.py:L3 off by one", True),
        ("**Verdict:** needs changes\n### Low\n- canary/pagination.py:3 naming", False),
        ("**Verdict:** ready\nLooks good.", False),
    ],
)
def test_review_grader(body, passed):
    result = grade_review(TASKS["review"], [mark("review", body)])
    assert result.passed is passed, result.reasons
    assert result.output == "https://gh/review" and result.kit == "v0.1.0"


def test_pr_grader_for_coding_and_test():
    pr = {**mark("coding", "Closes #12"), "draft": True}
    assert grade_pr("coding", [pr], checks="success", tests_ok=True, issue=12).passed
    bad = grade_pr("coding", [{**pr, "draft": False}], checks="failure", tests_ok=False, issue=13)
    assert bad.reasons == [
        "PR is not a draft",
        "PR does not close #13",
        "checks: failure",
        "hidden acceptance test failed",
    ]
    test_pr = {**mark("test", "Tests for round_money"), "draft": True}
    caught = grade_pr("test", [test_pr], checks="success", tests_ok=False, issue=None)
    assert caught.reasons == ["tests did not catch the bug"]


def test_sre_grader():
    good = "Impact: 5xx.\n```kql\nrequests | where success == false\n```\nCause: v1.4.0 KeyError 'currency'."
    assert grade_sre(TASKS["sre"], [mark("sre", good)]).passed
    vague = "```kql\ntraces | take 10\n```\nUnknown cause."
    assert grade_sre(TASKS["sre"], [mark("sre", vague)]).reasons == [
        "no ```kql block over requests or exceptions",
        "cause not named: v1.4.0",
        "cause not named: currency",
    ]


def test_feedback_grader():
    export = {**mark("feedback", "Users report CSV export timeouts"), "title": "Fix export timeouts"}
    dark = {**mark("feedback", "Several asks"), "title": "Add a dark theme"}
    assert grade_feedback(TASKS["feedback"], [export, dark]).passed
    assert grade_feedback(TASKS["feedback"], [export]).reasons == ["no Issue for theme alone: dark mode"]
    both = {**mark("feedback", "CSV export hangs and add dark mode"), "title": "Misc"}
    assert len(grade_feedback(TASKS["feedback"], [both]).reasons) == 2  # one Issue is not two clusters
    assert grade_feedback(TASKS["feedback"], [export] * 5 + [dark]).reasons == ["6 Issues, over the cap of 5"]
    assert not grade_feedback(TASKS["feedback"], []).passed


def test_canary_workflow_grades_every_task_as_astral_reads_it():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    grade = workflow["jobs"]["grade"]
    assert sorted(grade["strategy"]["matrix"]["agent"]) == sorted(TASKS)
    assert grade["name"] == "grade (${{ matrix.agent }})"
    assert re.search(r"\((?P<agent>[a-z][a-z0-9-]*)\)\s*$", "canary / grade (planner)")  # ASTRAL's parser
    for agent in TASKS:
        assert agent in workflow["jobs"], agent
    assert workflow["jobs"]["cleanup"]["if"].startswith("always()")


def test_release_is_gated_on_the_canary():
    text = (KIT_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert 'grep -qx "canary $GITHUB_SHA"' in text
    caller = (KIT_ROOT / "canary" / "caller.yml").read_text(encoding="utf-8")
    assert "run-name: canary ${{ github.event.client_payload.sha" in caller
