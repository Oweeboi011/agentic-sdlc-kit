"""Spec questions become decisions (ADR-0024 step 3): each `[NEEDS CLARIFICATION: …]` in a Spec Kit spec
opens one `needs-decision` Issue for the spec's code owners; the Issue closes once the marker is gone.

Deterministic, no model. Pure planning here; `main` reads the repo and calls `gh` (`issues: write` only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

QUESTION = re.compile(r"\[NEEDS CLARIFICATION:\s*([^\]]+?)\s*\]")
KEY = re.compile(r"<!--\s*kit-decision key=([0-9a-f]{12})\s*-->")
LABEL = "needs-decision"
SPECS = "specs/*/spec.md"
CODEOWNERS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
USER = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")


@dataclass(frozen=True)
class Question:
    spec: str
    line: int
    text: str

    @property
    def key(self) -> str:
        """Stable across line moves and whitespace edits; a reworded question is a new decision."""
        norm = " ".join(self.text.lower().split())
        return hashlib.sha256(f"{self.spec}\n{norm}".encode()).hexdigest()[:12]


def find_questions(spec: str, text: str) -> list[Question]:
    """Open questions in one spec, first occurrence of each."""
    found: dict[str, Question] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        for match in QUESTION.finditer(line):
            q = Question(spec, number, " ".join(match.group(1).split()))
            found.setdefault(q.key, q)
    return list(found.values())


def _rule(pattern: str) -> re.Pattern[str]:
    """CODEOWNERS pattern (gitignore-style subset) to a regex over repo paths."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    body = pattern.strip("/")
    out = ""
    for part in re.split(r"(\*\*/?|\*|\?)", body):
        if part == "**/":
            out += "(?:.*/)?"
        elif part == "**":
            out += ".*"
        elif part == "*":
            out += "[^/]*"
        elif part == "?":
            out += "[^/]"
        else:
            out += re.escape(part)
    prefix = "^" if anchored else "^(?:.*/)?"
    # `docs/*` owns direct children only; a plain name or `dir/` owns everything below it.
    suffix = "$" if body.endswith("*") and not body.endswith("**") else "(?:/.*)?$"
    return re.compile(prefix + out + suffix)


def owners(path: str, codeowners: str) -> list[str]:
    """Owners of `path`: the last matching CODEOWNERS rule wins (GitHub semantics)."""
    result: list[str] = []
    for raw in codeowners.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        pattern, *names = line.split()
        if _rule(pattern).match(path):
            result = names
    return result


def assignees(names: list[str]) -> list[str]:
    """Users can be assigned; teams and emails are only mentioned."""
    return [n[1:] for n in names if USER.match(n)][:10]


def title(q: Question) -> str:
    short = q.text if len(q.text) <= 80 else q.text[:79].rstrip() + "…"
    return f"Decision needed: {short}"


def body(q: Question, names: list[str], url: str = "") -> str:
    link = f"[{q.spec}:{q.line}]({url}/blob/HEAD/{q.spec}#L{q.line})" if url else f"`{q.spec}:{q.line}`"
    who = " ".join(names) if names else "_No code owner for this spec: add one in CODEOWNERS._"
    return (
        f"**Open question in {link}:**\n\n> {q.text}\n\n"
        f"**Decides:** {who}\n\n"
        "Answer here, then update the spec and remove the `[NEEDS CLARIFICATION]` marker. "
        "This Issue closes when the marker is gone.\n\n"
        f"<!-- kit-decision key={q.key} -->"
    )


def plan(questions: list[Question], open_issues: list[dict]) -> tuple[list[Question], list[int]]:
    """Questions without an open Issue, and kit decision Issues whose question is gone."""
    keys = {q.key for q in questions}
    tracked: dict[str, int] = {}
    for issue in open_issues:
        if m := KEY.search(issue.get("body") or ""):
            tracked.setdefault(m.group(1), issue["number"])
    create = [q for q in questions if q.key not in tracked]
    close = sorted(n for k, n in tracked.items() if k not in keys)
    return create, close


def scan(project: Path) -> tuple[list[Question], str]:
    questions = [
        q
        for spec in sorted(project.glob(SPECS))
        for q in find_questions(spec.relative_to(project).as_posix(), spec.read_text(encoding="utf-8"))
    ]
    text = next((f.read_text(encoding="utf-8") for c in CODEOWNERS if (f := project / c).is_file()), "")
    return questions, text


# --- I/O: gh (the project's own workflow) ----------------------------------------------------


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout.strip()


def _open_issues() -> list[dict]:
    out = _gh("issue", "list", "--label", LABEL, "--state", "open", "--limit", "1000",
              "--json", "number,body")  # fmt: skip
    return json.loads(out or "[]")


def _create(q: Question, names: list[str], url: str) -> str:
    args = ["issue", "create", "--title", title(q), "--body", body(q, names, url), "--label", LABEL]
    users = assignees(names)
    try:
        return _gh(*args, *(["--assignee", ",".join(users)] if users else []))
    except subprocess.CalledProcessError:
        if not users:
            raise
        return _gh(*args)  # an owner without repo access cannot be assigned; the body still names them


def main(argv: list[str] | None = None) -> int:
    about = "Open questions in specs become needs-decision Issues (ADR-0024)."
    parser = argparse.ArgumentParser(prog="kit-decisions", description=about)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true", help="print the plan; no gh calls")
    args = parser.parse_args(argv)
    questions, codeowners = scan(args.project)
    if args.dry_run:
        rows = [{**asdict(q), "key": q.key, "owners": owners(q.spec, codeowners)} for q in questions]
        print(json.dumps(rows, indent=2))
        return 0
    create, close = plan(questions, _open_issues())
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    url = f"{server}/{os.environ.get('GITHUB_REPOSITORY', '')}"
    for q in create:
        print(f"opened {_create(q, owners(q.spec, codeowners), url)}")
    for number in close:
        _gh("issue", "close", str(number), "--comment", "Resolved: the question is no longer in the spec.")
        print(f"closed #{number}")
    print(f"{len(questions)} open question(s); {len(create)} opened, {len(close)} closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
