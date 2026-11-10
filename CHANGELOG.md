# Changelog

All notable changes to this kit. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Skeleton: README, licence, code owners, DCO, CI (ruff, pytest, actionlint), release workflow (moving major tag), `kit-sync` entry point.
- JSON Schemas for agent frontmatter, skill frontmatter and a project's `.github/astral-kit.yml` (`schemas/`). Agents are propose-only (`human_gate.mode: propose`); skill names follow the [Agent Skills spec](https://agentskills.io/specification).
- `kit-sync --validate [--kit DIR] [--project DIR]`: schema checks plus name/file match and references to skills, MCP servers and kit agents. Exits 1 on any problem. CI runs it on the kit.
