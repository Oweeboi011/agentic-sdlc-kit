# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1 in progress. Done: skeleton (K1), schemas and validator (K2), renderer (K3). Content, reusable workflows and the sample project land next (K4–K8 in the plan).

## Use

From the project root, with a `.github/astral-kit.yml`:

```bash
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync           # render
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync --check   # CI: exit 1 on drift
```

`v0` is a moving tag on the newest `v0.x.y` release. `--validate` checks the kit (and `--project` config) only.

## What it renders

| Kit source | Copilot | Claude Code |
|---|---|---|
| `agents/<n>.md` (enabled in the config) | `.github/agents/<n>.agent.md` (tool aliases, `mcp-servers`) | `.claude/agents/<n>.md` (Claude tool names, `skills`, `mcpServers`) |
| `skills/<n>/SKILL.md` (used by an enabled agent) | `.github/skills/<n>/SKILL.md`, only when Claude Code is off | `.claude/skills/<n>/SKILL.md` (Copilot reads this folder too) |
| `instructions/<n>.md` (matching the stack) | `.github/instructions/<n>.instructions.md` (`applyTo`) | same files, listed in `AGENTS.md`; `applyTo: "**"` ones imported |
| kit rules + project gate | `AGENTS.md` | `.claude/CLAUDE.md` imports `@../AGENTS.md` |

- Every generated file carries a marker with the kit version and a sha256 of its content (after the frontmatter, which must stay on line 1). `--check` reports `missing`, `out of date`, `hand-edited` and `no longer rendered` files.
- Project text goes below the `<!-- project -->` line in `AGENTS.md` and `.claude/CLAUDE.md`; it is never touched. An existing hand-written `AGENTS.md` is adopted as that section.
- A file at a generated path without the marker belongs to the project: `kit-sync` writes nothing and reports the conflict.
- Formats were pinned on 2026-11-10 from the GitHub Copilot and Claude Code docs; they live only in `kit_sync/layouts.py`.

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
