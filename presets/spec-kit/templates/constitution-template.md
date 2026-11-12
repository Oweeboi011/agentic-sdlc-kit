# [PROJECT_NAME] Constitution

<!-- Generated from agentic-sdlc-kit instructions/ by `python -m kit_sync.preset`. -->

## Core Principles

### General

Applies to `**`.

- Scoped changes; root-cause fixes; reuse before creating; delete dead code.
- One responsibility per module; dependencies point inward; no import cycles.
- Never log or commit secrets, tokens or personal data.
- Comments only for non-obvious intent, at most two lines.
- Run the project gate (see `AGENTS.md`) before handing off.

## Engineering Standards

### Architecture decision records

Applies to `**/docs/adr/*.md`.

- One decision per ADR, next number, listed in the ADR index.
- Sections: Status, Date, Deciders · Context · Decision · Consequences · Alternatives · Related.
- New ADRs are `Proposed`. Accepted ADRs are append-only: supersede them with a new ADR; only edit status and links.
- Keep it short and specific to this repository.

### Bicep

Applies to `**/*.bicep` (stack: bicep; drop this section if the project does not use it).

- One module per resource type; parameters typed, with `@description` and safe defaults.
- Managed identity and RBAC over keys; no secrets in parameters or outputs (`@secure()` when unavoidable).
- Private endpoints and disabled public access for data services unless the reason is written down.
- Tag every resource; follow the project's naming pattern.
- `az bicep build` must pass with no warnings.

### Python

Applies to `**/*.py` (stack: python; drop this section if the project does not use it).

- Python 3.11+. Type hints on public functions. `ruff` for lint and format.
- Async for I/O; no blocking calls in async paths; use `httpx`, not `requests`.
- Raise specific exceptions; map them to HTTP status codes in one place.
- Configuration from environment variables; credentials from managed identity, never from code.
- Tests with `pytest`; mock at the process boundary, not internal modules.

### TypeScript and React

Applies to `**/*.ts,**/*.tsx` (stack: typescript-react; drop this section if the project does not use it).

- Strict TypeScript; no `any` (narrow `unknown`).
- Network calls only through the project's API client module; no inline `fetch` in components.
- Components small and typed; split when they grow past about 200 lines.
- No synchronous `setState` inside a `useEffect` body.
- Tests: Vitest + Testing Library for units and components, Playwright for user journeys.

## Delivery Rules

- **Spec first.** Features follow `specify` → `clarify` → `plan` → `tasks` → `analyze` → `implement`, with a human review after each step. A change with no new behaviour (fix, dependency, docs) may skip the spec; its PR says why.
- **Traceable.** Requirement IDs (FR-###, SC-###, NFR-###) appear in the backlog item, the PR body, test names and release notes.
- **Questions are decided, not guessed.** Each open `[NEEDS CLARIFICATION]` becomes a `needs-decision` backlog item for the spec's code owners; build waits for the decision.
- **Agents propose; humans decide.** Agents open draft PRs and proposals. Only humans merge, approve and deploy.
- **Gate before hand-off.** The project gate in `AGENTS.md` passes before a PR is marked ready.

## Governance

These rules come from the agentic SDLC kit (`instructions/`). Change them in the kit, then upgrade the kit; add project-specific principles as extra sections here. Amendments are reviewed by the code owners and recorded with a new version and date below.

[GOVERNANCE_RULES]

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
