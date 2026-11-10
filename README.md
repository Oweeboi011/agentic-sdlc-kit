# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1 in progress. This release has the skeleton only: CI, the release flow and the `kit-sync` entry point. Rendering, content and reusable workflows land item by item (K2–K8 in the plan).

## Use

```bash
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync --version
```

`v0` is a moving tag on the newest `v0.x.y` release.

## Develop

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # Windows; bin/ on Linux/macOS
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pytest -q
```

CI runs the same checks plus `actionlint` on every workflow.

## Rules

- Agents ship **propose-only**: no workflow merges, deploys or approves (ADR-0007, ADR-0014).
- Commits are signed off (`git commit -s`, DCO). PRs squash-merge into `main`.

## Release

1. Move the `Unreleased` notes in `CHANGELOG.md` under the new version and bump `version` in `pyproject.toml`.
2. Merge, then push a tag `vX.Y.Z` from `main`. The release workflow publishes the GitHub release from the changelog and moves the `vX` tag.
