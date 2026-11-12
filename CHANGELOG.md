# Changelog

All notable changes to this kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Skeleton: README, licence, code owners, DCO, CI (ruff, pytest, actionlint), release workflow (moving major tag), `kit-sync` entry point.
- JSON Schemas for agent frontmatter, skill frontmatter and a project's `.github/astral-kit.yml` (`schemas/`). Agents are propose-only (`human_gate.mode: propose`); skill names follow the [Agent Skills spec](https://agentskills.io/specification).
- `kit-sync --validate [--kit DIR] [--project DIR]`: schema checks plus name/file match and references to skills, MCP servers and kit agents. Exits 1 on any problem. CI runs it on the kit.
- `kit-sync` renderer: agents, skills and instructions into the Copilot and Claude Code layouts, `AGENTS.md` and `.claude/CLAUDE.md`. Marker with sha256 per file, `--check` for drift, `<!-- project -->` sections preserved, stale files removed, project-owned files never overwritten. Golden tests in `tests/fixtures/`.
- Instruction frontmatter schema (`applyTo`, optional `stack`) and MCP template checks in `--validate`.
- Content (K4): 7 propose-only agents (`planner`, `coding`, `review`, `test`, `release`, `sre`, `feedback`; one per stage 1-6 and 8), 9 skills, 5 instructions (`general`, `python`, `typescript-react`, `bicep`, `adr`), 3 MCP templates (`github` and `azure` read-only, `playwright`; versions pinned). Content ships inside the wheel, so `pipx run` renders it.
- Copilot layout: built-in `github`/`playwright` MCP servers are referenced, not redefined; `${NAME}` secrets become `${{ secrets.COPILOT_MCP_NAME }}`. Trigger `repository_dispatch:<type>` added for alert-driven agents.
- Reusable workflows (K5), `on: workflow_call` only: `ci-python`, `ci-node`, `security` (gitleaks with checksum check, dependency review on PRs), `iac-validate` (Bicep build + lint), `deploy-aca` (OIDC, keeps running images across re-provisioning, rolls apps and jobs, smoke test), `e2e-playwright` (report on failure), `kit-drift` (`kit-sync --check` at the pinned version). The kit's CI runs `ci-python` and `security`.
