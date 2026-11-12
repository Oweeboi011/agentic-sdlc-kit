"""K8: the committed sample project is exactly what kit-sync renders (E1) and drift is caught (E2)."""

import shutil
from pathlib import Path

import pytest

from kit_sync import __version__, cli
from kit_sync.sync import MARKER_RE

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-project"


def check(project: Path) -> int:
    return cli.main(["--check", "--project", str(project)])


def test_e1_sample_renders_both_layouts_and_is_in_sync(capsys):
    assert check(SAMPLE) == 0, capsys.readouterr().out
    assert (SAMPLE / ".github/agents/coding.agent.md").is_file()  # Copilot
    assert (SAMPLE / ".claude/agents/coding.md").is_file()  # Claude Code


def test_sample_markers_carry_the_kit_version():
    versions = {
        match[1]
        for path in SAMPLE.rglob("*")
        if path.is_file()
        for match in MARKER_RE.finditer(path.read_text(encoding="utf-8"))
    }
    assert versions == {f"v{__version__}"}, "re-render: kit-sync --project examples/sample-project"


@pytest.mark.parametrize(
    "rel", [".claude/agents/coding.md", ".github/ISSUE_TEMPLATE/story.yml", ".githooks/commit-msg"]
)
def test_e2_hand_edit_is_caught(tmp_path, capsys, rel):
    copy = tmp_path / "sample"
    shutil.copytree(SAMPLE, copy)
    with (copy / rel).open("a", encoding="utf-8") as f:
        f.write("edited by hand\n")
    assert check(copy) == 1
    assert f"{rel}: hand-edited" in capsys.readouterr().out


def test_project_text_and_starters_are_not_drift(tmp_path):
    copy = tmp_path / "sample"
    shutil.copytree(SAMPLE, copy)
    with (copy / "AGENTS.md").open("a", encoding="utf-8") as f:
        f.write("- More project notes.\n")
    (copy / ".github/CODEOWNERS").write_text("* @someone-else\n", encoding="utf-8")
    assert check(copy) == 0
