"""`kit-sync` command line. `--validate` checks kit content and project config; rendering lands in K3."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from kit_sync import __version__
from kit_sync.validate import validate_config, validate_kit

SOURCE_KIT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit-sync", description=__doc__)
    parser.add_argument("--version", action="version", version=f"kit-sync {__version__}")
    parser.add_argument("--validate", action="store_true", help="validate kit content (and --project config)")
    parser.add_argument("--kit", type=Path, default=SOURCE_KIT, help="kit root (default: this checkout)")
    parser.add_argument("--project", type=Path, help="project root holding .github/astral-kit.yml")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.validate:
        print(f"kit-sync {__version__}: rendering is not implemented yet (plan item K3).")
        return 0
    problems = validate_kit(args.kit)
    if args.project is not None:
        problems += validate_config(args.project, args.kit)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)" if problems else "valid")
    return 1 if problems else 0
