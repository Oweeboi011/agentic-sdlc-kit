# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1 in progress. Done: skeleton (K1), schemas and validator (K2), renderer (K3), content (K4: 7 agents, 9 skills, 5 instructions, 3 MCP templates), reusable workflows (K5). Agent workflows, templates and the sample project land next (K6–K8 in the plan).

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

## Reusable workflows

Call them from the project's own workflows, pinned to the kit's major tag:

```yaml
jobs:
  backend:
    uses: ava-innersource/agentic-sdlc-kit/.github/workflows/ci-python.yml@v0
    with:
      install: pip install -r requirements.txt -r requirements-dev.txt
      gate: python tools/harness.py ci   # the `gate` from .github/astral-kit.yml
```

| Workflow | Does | Key inputs | Caller grants |
|---|---|---|---|
| `ci-python` | setup-python, install, run the gate | `gate`, `install`, `python-version`, `cache-dependency-path`, `fetch-depth` | `contents: read` |
| `ci-node` | setup-node, `npm ci` in the package folder, run the gate from the root | `gate`, `package-directory`, `node-version`, `python-version` | `contents: read` |
| `security` | gitleaks over full history (pinned, checksum verified); on PRs dependency review | `gitleaks-config`, `fail-on-severity` (default `high`) | `contents: read`, `pull-requests: write` |
| `iac-validate` | `az bicep build` + `az bicep lint`, no Azure sign-in | `templates` (one per line) | `contents: read` |
| `deploy-aca` | OIDC sign-in, Bicep at RG scope (running images passed back in), build + push to ACR, roll Container Apps and Jobs, smoke test | `environment`, `images`, `parameters`, `template`, `health-fqdn-output`, `health-path` | `contents: read`, `id-token: write` |
| `e2e-playwright` | `npm ci`, browsers, build, test; HTML report uploaded on failure | `package-directory`, `build`, `test`, `browsers` | `contents: read` |
| `kit-drift` | `kit-sync --check` at the version pinned in `.github/astral-kit.yml` | `kit-version`; secret `kit-token` while the kit is not public | `contents: read` |

- `deploy-aca` reads `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and `AZURE_RESOURCE_GROUP` from the GitHub Environment, so its protection rules apply; no secrets are stored. Each `images` line is `<image-param> <app-output> <image-name> <build-context> [<job-output>...]`: the template takes the image in `<image-param>` and returns the app name in `<app-output>`.
- Commands passed as inputs reach scripts through `env`, never as inline expressions. Tests in `tests/test_workflows.py` enforce that, typed and documented inputs, pinned actions and no merge or approve step.
- The kit's CI calls `ci-python` and `security` itself, so every kit PR runs them.

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

- Agents ship **propose-only**: no workflow merges or approves, and agents never deploy (ADR-0007, ADR-0014). `deploy-aca` runs only from a project's own pipeline after a human merge.
- Commits are signed off (`git commit -s`, DCO). PRs squash-merge into `main`.

## Release

1. Move the `Unreleased` notes in `CHANGELOG.md` under the new version and bump `version` in `pyproject.toml`.
2. Merge, then push a tag `vX.Y.Z` from `main`. The release workflow publishes the GitHub release from the changelog and moves the `vX` tag.
