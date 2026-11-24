"""ADR-0024 step 3: spec questions become needs-decision Issues for the spec's code owners."""

import json

import yaml

from kit_sync.decisions import Question, assignees, body, find_questions, main, owners, plan, title
from kit_sync.paths import KIT_ROOT

SPEC = "specs/004-export/spec.md"
TEXT = """# Export
- **FR-001**: Users export invoices as CSV.
- **FR-002**: Dates use [NEEDS CLARIFICATION: which time zone?]
- **FR-003**: Retention [NEEDS CLARIFICATION:  how long   are exports kept? ] and
  again [NEEDS CLARIFICATION: Which  time zone?]
"""
CODEOWNERS = """
*                @org/platform
/specs/          @lead @org/product   # specs need product
docs/*           @writer
**/billing/**    @billing
"""


def test_finds_each_question_once_with_its_first_line():
    qs = find_questions(SPEC, TEXT)
    assert [(q.line, q.text) for q in qs] == [(3, "which time zone?"), (4, "how long are exports kept?")]


def test_key_survives_moves_and_whitespace_but_not_rewording():
    a = Question(SPEC, 3, "which time zone?")
    assert a.key == Question(SPEC, 40, "Which  time zone?").key
    assert a.key != Question(SPEC, 3, "which currency?").key
    assert a.key != Question("specs/005-x/spec.md", 3, "which time zone?").key


def test_last_matching_codeowners_rule_wins():
    assert owners(SPEC, CODEOWNERS) == ["@lead", "@org/product"]
    assert owners("src/app.py", CODEOWNERS) == ["@org/platform"]
    assert owners("docs/guide.md", CODEOWNERS) == ["@writer"]
    assert owners("docs/deep/guide.md", CODEOWNERS) == ["@org/platform"]  # docs/* = direct children only
    assert owners("src/billing/api/x.py", CODEOWNERS) == ["@billing"]
    assert owners(SPEC, "") == []


def test_only_users_are_assigned():
    assert assignees(["@lead", "@org/product", "dev@example.com"]) == ["lead"]


def test_plan_opens_new_questions_and_closes_answered_ones():
    asked, answered = find_questions(SPEC, TEXT)
    gone = Question(SPEC, 9, "old question")
    issues = [
        {"number": 7, "body": body(asked, [])},
        {"number": 8, "body": body(gone, [])},
        {"number": 9, "body": "A human's own needs-decision Issue"},
    ]
    create, close = plan([asked, answered], issues)
    assert create == [answered]
    assert close == [8]  # never #9: only Issues this tool opened


def test_issue_names_the_spec_line_owners_and_carries_the_key():
    q = Question(SPEC, 3, "which time zone?")
    text = body(q, ["@lead", "@org/product"], "https://github.com/org/repo")
    assert f"https://github.com/org/repo/blob/HEAD/{SPEC}#L3" in text
    assert "@lead @org/product" in text and f"kit-decision key={q.key}" in text
    assert "No code owner" in body(q, [])
    assert title(Question(SPEC, 1, "x" * 120)).endswith("…")


def test_dry_run_lists_questions_with_owners(tmp_path, capsys):
    (tmp_path / "specs/004-export").mkdir(parents=True)
    (tmp_path / SPEC).write_text(TEXT, encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/CODEOWNERS").write_text(CODEOWNERS, encoding="utf-8")
    assert main(["--project", str(tmp_path), "--dry-run"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["line"] for r in rows] == [3, 4]
    assert rows[0]["owners"] == ["@lead", "@org/product"]


def test_starter_runs_on_spec_changes_with_issue_write_only():
    path = KIT_ROOT / "templates/starters/github/workflows/spec-decisions.yml"
    wf = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert wf[True]["push"]["paths"] == ["specs/**/spec.md"]
    job = wf["jobs"]["decisions"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    assert job["uses"].endswith("/spec-decisions.yml@v0")
