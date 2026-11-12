"""`kit-sync`: render kit agents, skills, instructions and templates; `--check` fails on drift."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from kit_sync import __version__
from kit_sync.kit import load_config, load_files, load_kit
from kit_sync.paths import KIT_ROOT
from kit_sync.render import fill, render
from kit_sync.sync import apply, plan, write_starters
from kit_sync.validate import validate_config, validate_kit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit-sync", description=__doc__)
    parser.add_argument("--version", action="version", version=f"kit-sync {__version__}")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="exit 1 if rendered files are missing, stale or edited"
    )
    mode.add_argument(
        "--init", action="store_true", help="also write starter files the project lacks (then project-owned)"
    )
    mode.add_argument(
        "--validate", action="store_true", help="only validate kit content (and --project config)"
    )
    parser.add_argument("--kit", type=Path, default=KIT_ROOT, help="kit root (default: the installed kit)")
    parser.add_argument(
        "--project", type=Path, help="project root holding .github/astral-kit.yml (default: .)"
    )
    return parser


def _report(lines: Sequence[object], ok: str, failed: str) -> int:
    for line in lines:
        print(line)
    print(failed.format(len(lines)) if lines else ok)
    return 1 if lines else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate:
        problems = validate_kit(args.kit)
        if args.project is not None:
            problems += validate_config(args.project, args.kit)
        return _report(problems, "valid", "{} problem(s)")
    project = args.project or Path()
    problems = validate_kit(args.kit) + validate_config(project, args.kit)
    if problems:
        return _report(problems, "", "{} problem(s); nothing rendered")
    rendered = render(load_kit(args.kit), load_config(project))
    changes, conflicts = plan(project, rendered, f"v{__version__}")
    if args.check:
        return _report([*conflicts, *changes], "in sync", "{} file(s) drifted; run kit-sync")
    if conflicts:
        return _report(conflicts, "", "{} conflict(s); nothing written")
    apply(project, changes)
    if args.init:
        config = load_config(project)
        starters = load_files(args.kit / "templates" / "starters")
        created, kept = write_starters(project, {rel: fill(text, config) for rel, text in starters.items()})
        for line in [f"{rel}: created" for rel in created] + [f"{rel}: kept (project-owned)" for rel in kept]:
            print(line)
    return _report([], f"{len(changes)} file(s) updated, {len(rendered)} rendered", "")
