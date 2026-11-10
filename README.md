# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1 in progress. Done: skeleton (K1), schemas and validator (K2). Rendering, content and reusable workflows land item by item (K3–K8 in the plan).

## Use

```bash
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync --validate --project .
```

`v0` is a moving tag on the newest `v0.x.y` release.

## Schemas

| Schema | Validates |
|---|---|
| `schemas/agent.schema.json` | frontmatter of `agents/<name>.md`: `name`, `description`, `stage` (1–8), `triggers`, `skills`, `tools` (`read search edit execute todo web agent`), `mcp`, `permissions` (`GITHUB_TOKEN` scopes), `human_gate` (`mode: propose`, `reviewer`) |
| `schemas/skill.schema.json` | frontmatter of `skills/<name>/SKILL.md`: `name` (matches the folder, `a-z0-9-`, ≤64), `description` (≤1024) |
| `schemas/astral-kit.schema.json` | a project's `.github/astral-kit.yml`: `kit` (`v0` or `v0.1.0`), `runtimes` (`copilot`, `claude-code`), `stack`, `gate` (the project's own quality command), `agents`, optional `deploy` |

`kit-sync --validate` also checks that names match their file or folder and that every referenced skill, MCP server and agent exists in the kit.

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
