"""`kit-check`: generic repo checks any project's harness can call (comments, doc links, security inbox).

Each subcommand prints its findings and exits 1 when there are any. Run it from the repo root.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SOURCES = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs")
SKIP = r"(^|/)(tests?|node_modules|\.venv|dist|build)/|\.d\.ts$"
PY_COMMENT = re.compile(r"^\s*#(?!!)")
JS_COMMENT = re.compile(r"^\s*(//|\*|/\*)")
MD_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
REMOTE = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?\s")


def tracked(paths: Sequence[str], suffixes: tuple[str, ...]) -> list[str]:
    """Tracked files under `paths` (files or folders) with one of `suffixes`."""
    out = subprocess.run(["git", "ls-files", "--", *paths], capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f.endswith(suffixes)]


def comment_blocks(lines: Sequence[str], pattern: re.Pattern[str], limit: int) -> list[tuple[int, int]]:
    """(first line, length) of each run of comment lines longer than `limit`."""
    found, start = [], None
    for number, line in enumerate([*lines, ""], start=1):
        if pattern.match(line):
            start = start or number
            continue
        if start and number - start > limit:
            found.append((start, number - start))
        start = None
    return found


def long_docstrings(source: str, limit: int) -> list[tuple[int, int]]:
    """(line, length) of module, class and function docstrings longer than `limit` lines."""
    found = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc and (n := doc.count("\n") + 1) > limit:
                found.append((getattr(node, "lineno", 1), n))
    return found


def comment_findings(rel: str, source: str, max_block: int, max_docstring: int) -> list[str]:
    python = rel.endswith(".py")
    pattern = PY_COMMENT if python else JS_COMMENT
    found = [
        f"{rel}:{line} comment block {n} lines (max {max_block})"
        for line, n in comment_blocks(source.splitlines(), pattern, max_block)
    ]
    if python:
        found += [
            f"{rel}:{line} docstring {n} lines (max {max_docstring})"
            for line, n in long_docstrings(source, max_docstring)
        ]
    return found


def broken_links(rel: str, text: str) -> list[str]:
    """Relative Markdown links in `rel` whose target file doesn't exist."""
    base = Path(rel).parent
    return [
        f"{rel} -> {target} (missing)"
        for target in MD_LINK.findall(text)
        if not re.match(r"^[a-z][a-z0-9+.-]*:", target) and not target.startswith("/")
        if not (base / target).exists()
    ]


def _comments(args: argparse.Namespace) -> list[str]:
    skip = re.compile(args.skip)
    issues = []
    for rel in tracked(args.paths or ["."], SOURCES):
        path = Path(rel)
        if skip.search(rel) or not path.is_file():
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        issues += comment_findings(rel, source, args.max_block, args.max_docstring)
    return issues


def _doc_links(args: argparse.Namespace) -> list[str]:
    issues = []
    for rel in tracked(args.paths or ["."], (".md",)):
        path = Path(rel)
        if path.is_file():
            issues += broken_links(rel, path.read_text(encoding="utf-8", errors="ignore"))
    return issues


def _gh(*args: str) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh {' '.join(args)} failed")
    return proc.stdout


def github_repo(remotes: str) -> str:
    """owner/name of the first github.com remote in `git remote -v` output."""
    if match := REMOTE.search(remotes):
        return match.group(1)
    raise RuntimeError("no github.com remote")


def _dependabot(a: dict) -> str:
    dep = a["dependency"]
    return f"{a['security_advisory']['severity']:8} {dep['package']['name']} ({dep.get('manifest_path', '')})"


def _code_scanning(a: dict) -> str:
    loc = a["most_recent_instance"]["location"]
    severity = a["rule"].get("security_severity_level") or a["rule"]["severity"]
    return f"{severity:8} {a['rule']['id']} {loc['path']}:{loc['start_line']}"


def _secret(a: dict) -> str:
    return f"{'':8} {a['secret_type']}"


FEEDS = {
    "dependabot alert": ("dependabot/alerts", _dependabot),
    "code scanning": ("code-scanning/alerts", _code_scanning),
    "secret scanning": ("secret-scanning/alerts", _secret),
}


def _alerts(repo: str, label: str) -> list[str]:
    path, fmt = FEEDS[label]
    pages = json.loads(_gh("api", "--paginate", "--slurp", f"repos/{repo}/{path}?state=open&per_page=100"))
    return [f"{label:16} #{a['number']:<4} {fmt(a)}" for page in pages for a in page]


def _dependabot_prs(repo: str) -> list[str]:
    args = [
        "pr",
        "list",
        "-R",
        repo,
        "--author",
        "app/dependabot",
        "--limit",
        "1000",
        "--json",
        "number,title",
    ]
    return [f"{'dependabot PR':16} #{p['number']:<4} {'':8} {p['title']}" for p in json.loads(_gh(*args))]


def _security_inbox(args: argparse.Namespace) -> list[str]:
    repo = args.repo or github_repo(
        subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout
    )
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(_alerts, repo, label) for label in FEEDS]
        futures.append(pool.submit(_dependabot_prs, repo))
        return [line for future in futures for line in future.result()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit-check", description=__doc__)
    sub = parser.add_subparsers(dest="check", required=True)
    comments = sub.add_parser("comments", help="flag long comment blocks and Python docstrings")
    comments.add_argument("paths", nargs="*", help="files or folders (default: all tracked sources)")
    comments.add_argument("--max-block", type=int, default=6, help="longest comment block (lines)")
    comments.add_argument("--max-docstring", type=int, default=12, help="longest docstring (lines)")
    comments.add_argument("--skip", default=SKIP, help="regex of paths to skip")
    comments.set_defaults(run=_comments)
    links = sub.add_parser("doc-links", help="flag relative Markdown links to missing files")
    links.add_argument("paths", nargs="*", help="files or folders (default: all tracked .md)")
    links.set_defaults(run=_doc_links)
    inbox = sub.add_parser(
        "security-inbox", help="open Dependabot, code scanning, secret scanning alerts and Dependabot PRs"
    )
    inbox.add_argument("--repo", help="owner/name (default: the first github.com remote)")
    inbox.set_defaults(run=_security_inbox)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        issues = args.run(args)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"{args.check}: cannot run ({exc})")
        return 1
    for issue in issues:
        print(f"  {issue}")
    print(f"{args.check}: {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
