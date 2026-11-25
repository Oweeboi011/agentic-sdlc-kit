import json
import subprocess

import pytest

from kit_sync import checks


def _repo(tmp_path, files: dict[str, str]):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return tmp_path


def test_comment_block_over_limit_is_flagged():
    lines = ["x = 1", *["# note"] * 7, "y = 2"]
    assert checks.comment_blocks(lines, checks.PY_COMMENT, 6) == [(2, 7)]


def test_comment_block_at_limit_and_shebang_pass():
    lines = ["#!/usr/bin/env python", *["# note"] * 6, "y = 2"]
    assert checks.comment_blocks(lines, checks.PY_COMMENT, 6) == []


def test_js_comments_and_python_docstrings():
    js = "\n".join(["/**", *[" * line"] * 6, " */", "export const a = 1;"])
    assert checks.comment_findings("a.ts", js, 6, 12) == ["a.ts:1 comment block 8 lines (max 6)"]
    doc = '"""' + "\n".join(["line"] * 13) + '"""\n'
    assert checks.comment_findings("m.py", doc, 6, 12) == ["m.py:1 docstring 13 lines (max 12)"]


def test_unparsable_python_skips_docstrings():
    assert checks.long_docstrings("def (:", 12) == []


def test_broken_links_ignore_urls_anchors_and_absolute(tmp_path, monkeypatch):
    _repo(tmp_path, {"docs/a.md": "x", "docs/b.md": "x"})
    monkeypatch.chdir(tmp_path)
    text = "[ok](b.md) [anchor](b.md#top) [web](https://x.y) [mail](mailto:a@b) [abs](/c.md) [bad](c.md)"
    assert checks.broken_links("docs/a.md", text) == ["docs/a.md -> c.md (missing)"]


def test_github_repo_from_remotes():
    remotes = (
        "origin\thttps://dev.azure.com/o/p/_git/r (fetch)\ngithub\tgit@github.com:own/name.git (fetch)\n"
    )
    assert checks.github_repo(remotes) == "own/name"
    with pytest.raises(RuntimeError):
        checks.github_repo("origin\thttps://dev.azure.com/o/p/_git/r (fetch)\n")


def test_cli_comments_and_doc_links(tmp_path, monkeypatch, capsys):
    long = "\n".join(["# c"] * 7) + "\nx = 1\n"
    _repo(
        tmp_path,
        {"src/a.py": long, "tests/t.py": long, "README.md": "[gone](docs/none.md)", "src/ok.py": "x = 1\n"},
    )
    monkeypatch.chdir(tmp_path)
    assert checks.main(["comments"]) == 1
    out = capsys.readouterr().out
    assert "src/a.py:1 comment block 7 lines" in out and "tests/t.py" not in out
    assert checks.main(["comments", "src/ok.py"]) == 0
    assert checks.main(["doc-links"]) == 1
    assert "README.md -> docs/none.md (missing)" in capsys.readouterr().out


def test_security_inbox_lists_open_items(monkeypatch, capsys):
    replies = {
        "dependabot/alerts": [
            [
                {
                    "number": 3,
                    "security_advisory": {"severity": "high"},
                    "dependency": {"package": {"name": "lib"}, "manifest_path": "req.txt"},
                }
            ]
        ],
        "code-scanning/alerts": [[]],
        "secret-scanning/alerts": [[]],
    }

    def fake_gh(*args):
        if args[0] == "pr":
            return '[{"number": 9, "title": "bump lib"}]'
        feed = next(k for k in replies if k in args[-1])
        return json.dumps(replies[feed])

    monkeypatch.setattr(checks, "_gh", fake_gh)
    assert checks.main(["security-inbox", "--repo", "own/name"]) == 1
    out = capsys.readouterr().out
    assert "#3" in out and "lib (req.txt)" in out and "bump lib" in out and "2 issue(s)" in out
