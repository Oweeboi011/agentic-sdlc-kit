# Agentic SDLC Kit

One source of truth for the agents, skills, instructions, workflows, templates and policies that run agent-driven delivery, rendered into each project for **GitHub Copilot** and **Claude Code**.

Design: [ADR-0014](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0014-AGENTIC-SDLC-KIT.md). Plan: [Phase 2](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/solution-plan/PHASE-2-KIT-PLAN.md). Control plane: [ASTRAL AI](https://github.com/ava-innersource/icoe-astral-ai).

## Status

v0.1.0 (2026-11-25): skeleton (K1), schemas and validator (K2), renderer (K3), content (K4: 7 agents, 10 skills, 5 instructions, 4 MCP templates), reusable workflows (K5), agent workflows (K6), templates, policies and the Spec Kit preset (K7), sample project with CI checks E1–E3 (K8). Hosted at `Oweeboi011/agentic-sdlc-kit` (private) until `ava-innersource/agentic-sdlc-kit` exists: private-kit workflows are callable only from repos with the same owner.

## Use

From the project root, with a `.github/astral-kit.yml`:

```bash
pipx run --spec git+https://github.com/Oweeboi011/agentic-sdlc-kit@v0 kit-sync           # render
pipx run --spec git+https://github.com/Oweeboi011/agentic-sdlc-kit@v0 kit-sync --check   # CI: exit 1 on drift
pipx run --spec git+https://github.com/Oweeboi011/agentic-sdlc-kit@v0 kit-sync --init    # render + write missing starters
```

`v0` is a moving tag on the newest `v0.x.y` release. `--validate` checks the kit (and `--project` config) only.

`kit-check` holds generic checks a project's harness can call (exit 1 on findings):

```bash
kit-check comments [paths…] [--max-block 6] [--max-docstring 12]   # long comment blocks, Python docstrings
kit-check doc-links [paths…]                                        # relative Markdown links to missing files
kit-check security-inbox [--repo owner/name]                        # open security alerts + Dependabot PRs (gh, local)
```

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
    uses: Oweeboi011/agentic-sdlc-kit/.github/workflows/ci-python.yml@v0
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
| `deploy-aca` | OIDC sign-in, Bicep at RG scope (running images passed back in), build + push to ACR, roll Container Apps and Jobs, smoke test | `environment`, `images`, `parameters` (`${NAME}` / `${NAME:-default}` = the Environment's variable), `template`, `health-fqdn-output`, `health-path`; output `template-outputs` (JSON) | `contents: read`, `id-token: write` |
| `e2e-playwright` | `npm ci`, browsers, build, test; HTML report uploaded on failure | `package-directory`, `build`, `test`, `browsers` | `contents: read` |
| `hygiene` | `kit-check comments` (comment blocks > 6 lines, Python docstrings > 12) and `kit-check doc-links` (relative Markdown links to missing files), at the version pinned in `.github/astral-kit.yml` | `kit-version`, `comment-paths`, `max-comment-lines`, `max-docstring-lines` | `contents: read` |
| `kit-drift` | `kit-sync --check` at the version pinned in `.github/astral-kit.yml` | `kit-version`; secret `kit-token` while the kit is not public | `contents: read` |
| `spec-decisions` | `kit-decisions`: each `[NEEDS CLARIFICATION: …]` in `specs/*/spec.md` opens one `needs-decision` Issue assigned to the spec's code owners (users assigned, teams named); removing the marker closes it. No model ([ADR-0024](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0024-SPEC-DRIVEN-DEVELOPMENT-SPEC-KIT.md) step 3) | `kit-version`; secret `kit-token` | `contents: read`, `issues: write` |

- `deploy-aca` reads `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and `AZURE_RESOURCE_GROUP` from the GitHub Environment, so its protection rules apply; no secrets are stored. Each `images` line is `<image-param> <app-output> <image-name> <build-context> [<job-output>...]`: the template takes the image in `<image-param>` and returns the app name in `<app-output>`.
- Commands passed as inputs reach scripts through `env`, never as inline expressions. Tests in `tests/test_workflows.py` enforce that, typed and documented inputs, pinned actions and no merge or approve step.
- The kit's CI calls `ci-python` and `security` itself, so every kit PR runs them.

## Agent workflows

Propose-only agents on [Claude Code Action](https://github.com/anthropics/claude-code-action) (pinned to v1.0.271 by SHA), one per kit agent. The `agents.yml` starter calls them on their triggers; all run by hand too (`workflow_dispatch`).

| Workflow | Trigger (starter) | Does | Evidence | Caller grants |
|---|---|---|---|---|
| `planner` | label `needs-refinement` | Follows `.claude/agents/planner.md`: one refinement comment. Tools: read, `gh issue view`, `gh issue comment`. A human applies `ready` | Issue comment | `contents: read`, `issues: write`, `id-token: write` |
| `claude-code` | label `agent:claude` | Follows `.claude/agents/coding.md` on `agent/issue-<N>`: test-first change, project gate, **draft** PR with `Closes #N` | draft PR, `agent:claude` | `contents: write`, `pull-requests: write`, `issues: read`, `id-token: write` |
| `review` | PR opened or pushed (same repo) | One comment: `**Verdict:** ready` or `needs changes`, then ranked `file:line` findings. Tools: read, `gh pr view|diff|comment`, `git diff|log`; runs no PR code, never approves | PR comment | `contents: read`, `pull-requests: write`, `id-token: write` |
| `test` | label `agent:tests` (Issue or PR) | Adds tests on `agent/tests-<N>` as a **draft** PR (into the PR's branch for a PR). Guard fails on any changed file outside `test-files` | draft PR, `agent:tests` | `contents: write`, `pull-requests: write`, `issues: read`, `id-token: write` |
| `sre` | label `incident`, `repository_dispatch: alert` | Opens or reuses an `incident` Issue for an alert, then one triage comment: impact, timeline, KQL with results, probable cause, proposed mitigation or rollback. Azure read-only via the `environment` identity | Issue comment | `contents: read`, `issues: write`, `actions: read`, `deployments: read`, `id-token: write` |
| `feedback` | Mondays 06:00 UTC | Clusters `feedback` Issues of the last `days` into at most `max-issues` (5) Issues labelled `from-feedback` + `needs-refinement`; a guard closes any over the cap | Issues, `agent:feedback` | `contents: read`, `issues: write`, `id-token: write` |
| `release-agent` | by hand, `tag` | A **draft** release: notes by change type, risks, rollback plan. A guard turns anything it published back into a draft | draft release | `contents: write`, `pull-requests: read`, `deployments: read`, `id-token: write` |

- **Propose-only by construction.** `claude-code` and `test` deny `gh pr merge`, `gh pr review`, `gh pr ready` and force pushes. A guard step runs after the agent: it turns a non-draft PR back into a draft. The default branch must carry `policies/ruleset-main.json`, so the agent can't push to it. Comment agents get an allow list with no edit tools.
- **Evidence (ADR-0026).** Each agent's frontmatter declares `evidence` (`kind`, `label`, `trigger`). After the agent, `if: always()`, the workflow runs `.github/actions/agent-evidence`: it appends `<!-- agentic-sdlc-kit agent=<name> kit=<ver> run=<run_id> model=<model> -->` to every bot-authored output created during the run, puts the agent label on PRs and Issues, and writes the step summary and outputs `count` and `evidence-url`. The workflow, not the model, adds it, so prompt drift can't drop or forge it. ASTRAL reads the markers to show per agent whether it is installed, ran, produced its output and was accepted.
- **Claude endpoint** (plan A-03): `provider: anthropic` with secret `anthropic-api-key`, or `provider: foundry` with `foundry-base-url`, `model` (the Foundry deployment) and an `environment` whose vars hold `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (OIDC, no stored key).
- **CI on agent PRs needs a GitHub App** (ADR-0016): GitHub starts no workflows for pushes or PRs made with `GITHUB_TOKEN`. Pass secrets `app-id` and `app-private-key` to `claude-code` and `test`; they mint a short-lived App token (contents and pull requests write, issues read) for the push, the PR and the guard. Without them the draft PR opens but CI waits until a human pushes or re-runs it. The same applies to Issues the feedback agent opens: the planner starts on them only when a human re-applies `needs-refinement`.
- Issue, PR and alert text is passed as data, never as instructions. The action only runs for actors with write access.
- Toolchain for the gate (`claude-code`, `test`): `python-version`, `node-version`, `install` (as in `ci-python`).
- Each needs its agent rendered first (`kit-sync` with the agent in `agents`).

## Canary

Golden tasks prove the agents can still do their job (ADR-0026). `canary` (reusable) runs in a dedicated canary repo, created from `examples/sample-project` and onboarded in ASTRAL like any project; copy `canary/caller.yml` there as `.github/workflows/canary.yml` (daily, by hand, or on `repository_dispatch: kit-candidate` with a kit `sha`).

1. **Seed** (`kit-canary seed`): one input per task in `canary/tasks/*.yml`: a story for the planner, a PR with a planted bug at a known `file:line` for review, a small spec for coding (the acceptance test stays hidden), an untested function for test (as a PR), a synthetic Azure Monitor alert for SRE, six `feedback` Issues with two themes.
2. **Run** each agent workflow on its seed, from the kit's `main`.
3. **Grade** (`kit-canary grade`, job `grade (<agent>)`), deterministic: planner has every story section and 3–7 criteria; review names the planted line as high or medium; coding's draft PR closes the issue, has green checks and passes the hidden test; test's tests pass on the function and fail on the planted bug; SRE cites `requests`/`exceptions` KQL and the cause; feedback finds both themes within its cap. Each writes `canary-results-<agent>.json` (pass, reasons, kit, model, output, kit sha) as an artifact and the step summary.
4. **Clean up** (`kit-canary cleanup`): seeds, agent PRs and Issues of the run are closed, seed branches deleted.

ASTRAL reads the latest completed run's `grade (<agent>)` jobs into the Canary column of Agent health. The kit `Release` workflow refuses a tag unless the canary repo (`vars.CANARY_REPO`, read with `secrets.CANARY_READ_TOKEN`) has a passing run titled `canary <sha>` for the tagged commit; with `CANARY_REPO` unset the gate is off. Needs a Claude endpoint, and the GitHub App (ADR-0016) for CI on the coding and test PRs.

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

## Sample project

`examples/sample-project/` is a project with every runtime, stack, agent and template group enabled, committed exactly as `kit-sync --init` rendered it. Kit CI proves the exit criteria against the installed wheel:

- **E1:** `kit-sync --check` on the sample passes, so both layouts render and match.
- **E2:** a hand edit in a copy of the sample fails `--check` with `hand-edited`.
- **E3:** `actionlint` covers the kit's workflows and the sample's starter workflows.

Project text in its `AGENTS.md` (below `<!-- project -->`) and its starters are not drift.

## Schemas

| Schema | Validates |
|---|---|
| `schemas/agent.schema.json` | frontmatter of `agents/<name>.md`: `name`, `description`, `stage` (1–8), `triggers`, `skills`, `tools` (`read search edit execute todo web agent`), `mcp`, `permissions` (`GITHUB_TOKEN` scopes), `human_gate` (`mode: propose`, `reviewer`), `evidence` (`kind`, `label`, `trigger`: what the agent leaves behind, ADR-0026) |
| `schemas/skill.schema.json` | frontmatter of `skills/<name>/SKILL.md`: `name` (matches the folder, `a-z0-9-`, ≤64), `description` (≤1024) |
| `schemas/astral-kit.schema.json` | a project's `.github/astral-kit.yml`: `kit` (`v0` or `v0.1.0`), `runtimes` (`copilot`, `claude-code`), `stack`, `gate` (the project's own quality command), `agents`, optional `templates` and `deploy` |

`kit-sync --validate` also checks that names match their file or folder, that every referenced skill, MCP server and agent exists in the kit, and that `evidence.trigger` is one of the agent's triggers.

## Develop

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # Windows; bin/ on Linux/macOS
.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pytest -q
```

CI runs the same checks plus `actionlint` on every workflow.

## Rules

- Agents ship **propose-only**: no workflow merges or approves, and agents never deploy (ADR-0007, ADR-0014). `deploy-aca` runs only from a project's own pipeline after a human merge.
- Commits: conventional subject, no `Signed-off-by` trailer (kit repo rule; agents follow each project's rules). PRs squash-merge into `main`.

## Release

1. Move the `Unreleased` notes in `CHANGELOG.md` under the new version and bump `version` in `pyproject.toml` and `presets/spec-kit/preset.yml`.
2. Reinstall (`pip install -e ".[dev]"`) and re-render the sample, whose markers carry the version: `kit-sync --project examples/sample-project`.
3. Merge, then push a tag `vX.Y.Z` from `main`. The release workflow publishes the GitHub release from the changelog, attaches `spec-kit-preset.zip` and moves the `vX` tag.
