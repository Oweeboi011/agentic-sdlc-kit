# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows, templates and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1 in progress. Done: skeleton (K1), schemas and validator (K2), renderer (K3), content (K4: 7 agents, 9 skills, 5 instructions, 3 MCP templates), reusable workflows (K5), agent workflows (K6), templates, policies and the Spec Kit preset (K7). The sample project and `v0.1.0` land next (K8 in the plan).

## Use

From the project root, with a `.github/astral-kit.yml`:

```bash
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync           # render
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync --check   # CI: exit 1 on drift
pipx run --spec git+https://github.com/ava-innersource/agentic-sdlc-kit@v0 kit-sync --init    # render + write missing starters
```

`v0` is a moving tag on the newest `v0.x.y` release. `--validate` checks the kit (and `--project` config) only.

## What it renders

| Kit source | Copilot | Claude Code |
|---|---|---|
| `agents/<n>.md` (enabled in the config) | `.github/agents/<n>.agent.md` (tool aliases, `mcp-servers`) | `.claude/agents/<n>.md` (Claude tool names, `skills`, `mcpServers`) |
| `skills/<n>/SKILL.md` (used by an enabled agent) | `.github/skills/<n>/SKILL.md`, only when Claude Code is off | `.claude/skills/<n>/SKILL.md` (Copilot reads this folder too) |
| `instructions/<n>.md` (matching the stack) | `.github/instructions/<n>.instructions.md` (`applyTo`) | same files, listed in `AGENTS.md`; `applyTo: "**"` ones imported |
| kit rules + project gate | `AGENTS.md` | `.claude/CLAUDE.md` imports `@../AGENTS.md` |
| `templates/managed/` (enabled groups) | issue forms, PR template, `.githooks/commit-msg` | same files |

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

## Agent workflows

Propose-only agents on [Claude Code Action](https://github.com/anthropics/claude-code-action) (pinned to v1.0.271 by SHA). The `agents.yml` starter calls them on labels; both also run by hand (`workflow_dispatch`).

| Workflow | Trigger (starter) | Does | Caller grants |
|---|---|---|---|
| `planner` | label `needs-refinement` | Follows `.claude/agents/planner.md`: posts one refinement comment. Tools: read, `gh issue view`, `gh issue comment` only. A human applies `ready` | `contents: read`, `issues: write`, `id-token: write` |
| `claude-code` | label `agent:claude` | Follows `.claude/agents/coding.md` on branch `agent/issue-<N>`: test-first change, project gate, signed-off commits, **draft** PR with `Closes #N` | `contents: write`, `pull-requests: write`, `issues: read`, `id-token: write` |

- **Propose-only by construction.** `claude-code` denies `gh pr merge`, `gh pr review`, `gh pr ready` and force pushes. A guard step runs after the agent: it turns a non-draft PR back into a draft, and fails the run (with a PR comment) if any commit lacks a `Signed-off-by` matching its author (DCO, plan R-07). The default branch must carry `policies/ruleset-main.json`, so the agent can't push to it.
- **Claude endpoint** (plan A-03): `provider: anthropic` with secret `anthropic-api-key`, or `provider: foundry` with `foundry-base-url`, `model` (the Foundry deployment) and an `environment` whose vars hold `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (OIDC, no stored key).
- **CI on agent PRs needs a GitHub App** (ADR-0016): GitHub starts no workflows for pushes or PRs made with `GITHUB_TOKEN`. Pass secrets `app-id` and `app-private-key` to `claude-code`; it mints a short-lived App token (contents and pull requests write, issues read) for the push, the PR and the guard. Without them the draft PR opens but CI waits until a human pushes or re-runs it.
- Issue text is passed as data, never as instructions. The action only runs for actors with write access.
- Toolchain for the gate: `python-version`, `node-version`, `install` (as in `ci-python`).
- Both need the agents rendered first (`kit-sync` with `planner` and `coding` in `agents`).

## Templates, starters and policies

| Kind | Files | How it reaches the project |
|---|---|---|
| Managed templates (`templates/managed/`) | issue forms `story`, `bug`, `decision` (`needs-decision`), `feedback`, `config.yml`; `.github/pull_request_template.md`; `.githooks/commit-msg` | Rendered by `kit-sync` with the marker and checked by `--check`, like agents. Groups `issue-forms`, `pr-template`, `githooks` (`templates` in the config; default: all). The PR template keeps project checklist items below `<!-- project -->`. Hooks are written executable; enable once per clone with `git config core.hooksPath .githooks` |
| Starters (`templates/starters/`) | `.github/CODEOWNERS`, `.github/dependabot.yml`, `.github/workflows/ci.yml` (calls the kit's reusable workflows with the project gate), `.github/workflows/agents.yml` (agent workflows on labels), `.github/workflows/copilot-setup-steps.yml` | `kit-sync --init` writes the ones the project lacks, without a marker. From then on the project owns them: they differ per repo (owners, ecosystems, toolchain) |
| Policies (`policies/`) | `ruleset-main.json`, `environments.json`, `labels.json` | Applied with `gh api` (below); ASTRAL's guardrails check the result |

`{{gate}}` in a template or starter becomes the project's `gate`.

Apply the policies (needs repo admin; `REPO=owner/name`, run from a kit clone):

```bash
# main ruleset: no deletion or force push, 1 approval incl. code owner, last-push approval, squash, CodeQL
gh api -X POST "repos/$REPO/rulesets" --input policies/ruleset-main.json
# add required checks to it (names as GitHub shows them, e.g. "gate / python"):
#   jq '.rules += [{type:"required_status_checks",parameters:{strict_required_status_checks_policy:false,
#     required_status_checks:[{context:"gate / python"},{context:"security / secrets (gitleaks)"}]}}]'

# environments dev, staging, prod: deploy from main only; prod needs reviewers (set them first)
jq -e '.prod.settings.reviewers | length > 0' policies/environments.json > /dev/null || echo "set prod reviewers first"
for env in dev staging prod; do
  jq ".\"$env\".settings" policies/environments.json | gh api -X PUT "repos/$REPO/environments/$env" --input -
  for branch in $(jq -r ".\"$env\".branches[]" policies/environments.json); do
    gh api -X POST "repos/$REPO/environments/$env/deployment-branch-policies" -f name="$branch" -f type=branch
  done
done

# labels the agents trigger on
jq -c '.[]' policies/labels.json | while read -r label; do
  gh label create "$(jq -r .name <<< "$label")" --repo "$REPO" --force \
    --color "$(jq -r .color <<< "$label")" --description "$(jq -r .description <<< "$label")"
done
```

Prod reviewers are `{"type": "User" | "Team", "id": <number>}` (`gh api users/<login> -q .id`, `gh api orgs/<org>/teams/<slug> -q .id`).

## Spec Kit preset

`presets/spec-kit/` is a [Spec Kit](https://github.com/github/spec-kit) org preset (ADR-0024), pinned to Spec Kit `~=1.4.0`. It appends non-functional (NFR-###), security, data-handling and traceability sections to `spec-template`, and replaces `constitution-template` with one generated from `instructions/` (`python -m kit_sync.preset`; a test fails while it is stale). Each release attaches it as `spec-kit-preset.zip`. Install: [presets/spec-kit/README.md](presets/spec-kit/README.md).

## Schemas

| Schema | Validates |
|---|---|
| `schemas/agent.schema.json` | frontmatter of `agents/<name>.md`: `name`, `description`, `stage` (1–8), `triggers`, `skills`, `tools` (`read search edit execute todo web agent`), `mcp`, `permissions` (`GITHUB_TOKEN` scopes), `human_gate` (`mode: propose`, `reviewer`) |
| `schemas/skill.schema.json` | frontmatter of `skills/<name>/SKILL.md`: `name` (matches the folder, `a-z0-9-`, ≤64), `description` (≤1024) |
| `schemas/astral-kit.schema.json` | a project's `.github/astral-kit.yml`: `kit` (`v0` or `v0.1.0`), `runtimes` (`copilot`, `claude-code`), `stack`, `gate` (the project's own quality command), `agents`, optional `templates` and `deploy` |

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

1. Move the `Unreleased` notes in `CHANGELOG.md` under the new version and bump `version` in `pyproject.toml` and `presets/spec-kit/preset.yml`.
2. Merge, then push a tag `vX.Y.Z` from `main`. The release workflow publishes the GitHub release from the changelog, attaches `spec-kit-preset.zip` and moves the `vX` tag.
