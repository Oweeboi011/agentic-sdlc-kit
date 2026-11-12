"""Canary golden tasks (ADR-0026): seed known inputs in the canary repo, grade each agent's output
deterministically, clean up. Graders are pure; `seed`, `grade` and `cleanup` call `gh` and `git`.

Runs only in the canary repo's own workflow (`canary.yml`); ASTRAL reads the job results, never writes.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

MARKER = re.compile(r"<!--\s*agentic-sdlc-kit agent=([a-z][a-z0-9-]*) kit=(\S+) run=(\d+) model=(\S+)\s*-->")
SEVERITY = re.compile(r"\b(high|medium|low)\b", re.I)
CRITERION = re.compile(r"^\s*(?:[-*+]|\d+[.)]|- \[[ x]\])\s+\S")
CANARY_LABEL = "canary"


@dataclass
class Result:
    agent: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    output: str | None = None
    kit: str | None = None
    model: str | None = None

    def fail(self, reason: str) -> Result:
        self.passed = False
        self.reasons.append(reason)
        return self


def load_tasks(folder: Path) -> dict[str, dict]:
    tasks = {}
    for path in sorted(folder.glob("*.yml")):
        task = yaml.safe_load(path.read_text(encoding="utf-8"))
        tasks[task["agent"]] = task
    return tasks


def marked(items: list[dict], agent: str) -> list[dict]:
    """Items whose body carries `agent`'s evidence marker, oldest first."""
    out = [i for i in items if (m := MARKER.search(i.get("body") or "")) and m.group(1) == agent]
    return sorted(out, key=lambda i: i.get("created_at") or "")


def _start(agent: str, items: list[dict]) -> tuple[Result, dict | None]:
    found = marked(items, agent)
    result = Result(agent, True)
    if not found:
        return result.fail(f"no {agent} output with the evidence marker"), None
    item = found[-1]
    mark = MARKER.search(item["body"])
    result.output, result.kit, result.model = item.get("html_url"), mark.group(2), mark.group(4)
    return result, item


_KNOWN = ("acceptance criteria", "open questions", "out of scope", "test notes", "estimate", "goal")


def _label(line: str) -> str | None:
    """Section name when `line` is a label (`## Goal`, `**Goal:**`, `- **Goal:** ...`, `Goal:`)."""
    text = line.strip().lstrip("#-* ").lower()
    for name in _KNOWN:
        rest = text[len(name) :] if text.startswith(name) else None
        labelled = line.lstrip().startswith("#") or "**" in line
        if rest is not None and (labelled or rest.lstrip("*").startswith(":")):
            return name
    return None


def _sections(body: str) -> dict[str, list[str]]:
    """Lines under each section label, keyed by the lower-case label."""
    out: dict[str, list[str]] = {}
    current = None
    for line in body.splitlines():
        name = _label(line)
        if name:
            current = name
            out.setdefault(current, [])
        elif current:
            out[current].append(line)
    return out


def grade_planner(task: dict, comments: list[dict]) -> Result:
    result, comment = _start("planner", comments)
    if comment is None:
        return result
    sections = _sections(comment["body"])
    for name in task["expected"]["sections"]:
        if name not in sections:
            result.fail(f"missing section: {name}")
    criteria = [line for line in sections.get("acceptance criteria", []) if CRITERION.match(line)]
    low, high = task["expected"]["min_criteria"], task["expected"]["max_criteria"]
    if not low <= len(criteria) <= high:
        result.fail(f"{len(criteria)} acceptance criteria, expected {low}-{high}")
    return result


def grade_review(task: dict, comments: list[dict]) -> Result:
    result, comment = _start("review", comments)
    if comment is None:
        return result
    path, line = task["expected"]["path"], task["expected"]["line"]
    wanted = {s.lower() for s in task["expected"]["severities"]}
    where = re.compile(rf"{re.escape(path)}:L?(\d+)")
    heading = None  # severity of the section a finding sits in (`### High`)
    for text in comment["body"].splitlines():
        own = SEVERITY.search(text)
        hits = [int(n) for n in where.findall(text)]
        if not hits:
            heading = own.group(1).lower() if own else heading
            continue
        if any(abs(n - line) <= 1 for n in hits):
            rank = own.group(1).lower() if own else heading
            if rank in wanted:
                return result
            expected = "/".join(sorted(wanted))
            return result.fail(f"{path}:{line} named as {rank or 'unranked'}, expected {expected}")
    return result.fail(f"planted bug {path}:{line} not named")


def grade_pr(agent: str, prs: list[dict], *, checks: str | None, tests_ok: bool, issue: int | None) -> Result:
    """coding / test: a draft PR with the marker, green checks and the hidden or bug test result."""
    result, pr = _start(agent, prs)
    if pr is None:
        return result
    if not pr.get("draft"):
        result.fail("PR is not a draft")
    if issue is not None and not re.search(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#{issue}\b",
                                           pr.get("body") or "", re.I):  # fmt: skip
        result.fail(f"PR does not close #{issue}")
    if checks != "success":
        result.fail(f"checks: {checks or 'none'}")
    if not tests_ok:
        result.fail("hidden acceptance test failed" if agent == "coding" else "tests did not catch the bug")
    return result


def grade_sre(task: dict, comments: list[dict]) -> Result:
    result, comment = _start("sre", comments)
    if comment is None:
        return result
    body = comment["body"]
    blocks = " ".join(re.findall(r"```kql\s*\n(.*?)```", body, re.S | re.I)).lower()
    if not any(table in blocks for table in task["expected"]["kql"]):
        result.fail(f"no ```kql block over {' or '.join(task['expected']['kql'])}")
    for token in task["expected"]["cause"]:
        if token.lower() not in body.lower():
            result.fail(f"cause not named: {token}")
    return result


def grade_feedback(task: dict, issues: list[dict]) -> Result:
    found = marked(issues, "feedback")
    result = Result("feedback", True, output=found[0].get("html_url") if found else None)
    if not found:
        return result.fail("no from-feedback Issue with the evidence marker")
    if len(found) > task["expected"]["max_issues"]:
        result.fail(f"{len(found)} Issues, over the cap of {task['expected']['max_issues']}")
    texts = [f"{i.get('title', '')} {i.get('body') or ''}".lower() for i in found]
    for theme, words in task["expected"]["themes"].items():
        if not any(any(w in t for w in words) for t in texts):
            result.fail(f"theme not found: {theme}")
    return result


# --- I/O: gh and git (canary repo only) -----------------------------------------------------


def _gh(*args: str, data: str | None = None) -> str:
    done = subprocess.run(["gh", *args], input=data, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _api(path: str, *fields: str, method: str = "GET") -> Any:
    flags = [f for pair in (("-f", x) for x in fields) for f in pair]
    out = _gh("api", "-X", method, path, *flags)
    return json.loads(out) if out else None


def _repo() -> str:
    return os.environ["GITHUB_REPOSITORY"]


def _branch_with(name: str, files: dict[str, str]) -> str:
    repo = _repo()
    base = _api(f"repos/{repo}")["default_branch"]
    sha = _api(f"repos/{repo}/git/ref/heads/{base}")["object"]["sha"]
    _api(f"repos/{repo}/git/refs", f"ref=refs/heads/{name}", f"sha={sha}", method="POST")
    for path, text in files.items():
        content = base64.b64encode(text.encode()).decode()
        _api(f"repos/{repo}/contents/{path}", f"message=canary: seed {path}", f"content={content}",
             f"branch={name}", method="PUT")  # fmt: skip
    return name


def _issue(title: str, body: str, *labels: str) -> int:
    flags = [a for label in labels for a in ("--label", label)]
    url = _gh("issue", "create", "--title", title, "--body", body, *flags)
    return int(url.rsplit("/", 1)[-1])


def _seed_one(task: dict, run: str) -> dict:
    kind = task["seed"]
    if kind == "issue":
        return {"number": _issue(task["title"], task["body"], CANARY_LABEL)}
    if kind == "pr":
        branch = _branch_with(f"canary/{task['agent']}-{run}", task["files"])
        url = _gh("pr", "create", "--head", branch, "--title", task["title"], "--body", task["body"],
                  "--label", CANARY_LABEL)  # fmt: skip
        return {"number": int(url.rsplit("/", 1)[-1]), "branch": branch}
    if kind == "alert":
        return {"number": 0, "alert": json.dumps(task["alert"])}
    numbers = [_issue(title, "Canary feedback.", "feedback", CANARY_LABEL) for title in task["issues"]]
    return {"number": 0, "issues": numbers}


def seed(tasks: dict[str, dict], run: str) -> dict:
    """Create every task's input; the test task becomes a PR so the agent's tests target its branch."""
    since = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    seeds = {}
    for agent, task in tasks.items():
        if agent == "test":
            task = {**task, "seed": "pr"}
        seeds[agent] = _seed_one(task, run)
    return {"since": since, "run": run, "seeds": seeds}


def _since(items: list[dict], since: str) -> list[dict]:
    return [i for i in items if (i.get("created_at") or "") >= since]


def _comments(number: int, since: str) -> list[dict]:
    return _since(_api(f"repos/{_repo()}/issues/{number}/comments?per_page=100") or [], since)


def _agent_pr(branch: str) -> dict | None:
    owner = _repo().split("/")[0]
    prs = _api(f"repos/{_repo()}/pulls?head={owner}:{branch}&state=all") or []
    return prs[0] if prs else None


def _checks(sha: str) -> str | None:
    runs = (_api(f"repos/{_repo()}/commits/{sha}/check-runs?per_page=100") or {}).get("check_runs", [])
    runs = [r for r in runs if not r["name"].startswith("grade")]
    if not runs or any(r["status"] != "completed" for r in runs):
        return None
    return "success" if all(r["conclusion"] in ("success", "skipped", "neutral") for r in runs) else "failure"


def _run(command: str) -> bool:
    return subprocess.run(command, shell=True, check=False).returncode == 0


def _checkout(branch: str) -> None:
    subprocess.run(["git", "fetch", "-q", "origin", branch], check=True)
    subprocess.run(["git", "checkout", "-q", "-f", "FETCH_HEAD"], check=True)


def _write(files: dict[str, str]) -> None:
    for path, text in files.items():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")


def _grade_pr_task(agent: str, task: dict, seeded: dict) -> Result:
    branch = f"agent/issue-{seeded['number']}" if agent == "coding" else f"agent/tests-{seeded['number']}"
    pr = _agent_pr(branch)
    if pr is None:
        return Result(agent, False, [f"no PR from {branch}"])
    _checkout(branch)
    if agent == "coding":
        _write({task["hidden_test"]["path"]: task["hidden_test"]["content"]})
        ok = _run(task["hidden_test"]["command"])
    else:
        ok = _run(task["command"])
        _write(task["bug"])
        ok = ok and not _run(task["command"])
    issue = seeded["number"] if agent == "coding" else None
    return grade_pr(agent, [pr], checks=_checks(pr["head"]["sha"]), tests_ok=ok, issue=issue)


def _incident(since: str) -> int | None:
    issues = _api(f"repos/{_repo()}/issues?labels=incident&state=all&since={since}") or []
    found = [i for i in _since(issues, since) if "[canary]" in i["title"]]
    return found[0]["number"] if found else None


def grade(agent: str, task: dict, state: dict) -> Result:
    seeded, since = state["seeds"][agent], state["since"]
    if agent in ("coding", "test"):
        return _grade_pr_task(agent, task, seeded)
    if agent == "feedback":
        issues = _api(f"repos/{_repo()}/issues?labels=from-feedback&state=all&since={since}") or []
        return grade_feedback(task, _since(issues, since))
    if agent == "sre":
        number = _incident(since)
        return grade_sre(task, _comments(number, since)) if number else Result("sre", False, ["no incident"])
    graders = {"planner": grade_planner, "review": grade_review}
    return graders[agent](task, _comments(seeded["number"], since))


def cleanup(state: dict) -> None:
    """Close every seed and agent output of this run; delete seed branches."""
    repo, since = _repo(), state["since"]
    note = "Closed by the canary run."
    for seeded in state["seeds"].values():
        kind = "pr" if seeded.get("branch") else "issue"
        for n in filter(None, [seeded["number"], *seeded.get("issues", [])]):
            _gh(kind, "close", str(n), "--comment", note)
        if seeded.get("branch"):
            _api(f"repos/{repo}/git/refs/heads/{seeded['branch']}", method="DELETE")
    opened = _api(f"repos/{repo}/issues?labels=from-feedback&state=open&since={since}") or []
    for issue in _since(opened, since):
        _gh("issue", "close", str(issue["number"]), "--comment", note)
    incident = _incident(since)
    if incident:
        _gh("issue", "close", str(incident), "--comment", note)
    for branch in (f"agent/issue-{state['seeds']['coding']['number']}",
                   f"agent/tests-{state['seeds']['test']['number']}"):  # fmt: skip
        pr = _agent_pr(branch)
        if pr and pr["state"] == "open":
            _gh("pr", "close", str(pr["number"]), "--delete-branch", "--comment", note)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kit-canary", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["seed", "grade", "cleanup"])
    parser.add_argument("--tasks", type=Path, default=Path("canary/tasks"))
    parser.add_argument("--state", type=Path, default=Path("canary-state.json"))
    parser.add_argument("--agent", help="grade: agent to grade")
    parser.add_argument("--out", type=Path, default=Path("canary-results.json"))
    args = parser.parse_args(argv)
    tasks = load_tasks(args.tasks)
    if args.command == "seed":
        state = seed(tasks, os.environ.get("GITHUB_RUN_ID", "local"))
        args.state.write_text(json.dumps(state), encoding="utf-8")
        return 0
    state = json.loads(args.state.read_text(encoding="utf-8"))
    if args.command == "cleanup":
        cleanup(state)
        return 0
    result = grade(args.agent, tasks[args.agent], state)
    args.out.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    print(f"{result.agent}: {'pass' if result.passed else 'fail'} {'; '.join(result.reasons)}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
