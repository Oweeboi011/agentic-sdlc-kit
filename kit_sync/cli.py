"""`kit-sync` command line. Rendering arrives in K3; v0.1 skeleton only reports its version."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from kit_sync import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kit-sync", description=__doc__)
    parser.add_argument("--version", action="version", version=f"kit-sync {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(f"kit-sync {__version__}: rendering is not implemented yet (plan item K3).")
    return 0
