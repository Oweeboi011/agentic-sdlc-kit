# Agentic SDLC org preset for Spec Kit

A [Spec Kit](https://github.com/github/spec-kit) preset ([ADR-0024](https://github.com/ava-innersource/icoe-astral-ai/blob/main/docs/adr/0024-SPEC-DRIVEN-DEVELOPMENT-SPEC-KIT.md)):

- `spec-template` (append): non-functional (NFR-###), security and privacy, data-handling and traceability sections.
- `constitution-template` (replace): generated from the kit's `instructions/` by `python -m kit_sync.preset`, so agents and specs follow one set of rules. Don't edit it by hand.

Requires Spec Kit `~=1.4.0` (pinned; upgrades ship as kit releases).

## Install in a project

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.4.0
specify init --here                                   # once per project
specify preset add --from https://github.com/ava-innersource/agentic-sdlc-kit/releases/download/v0.1.0/spec-kit-preset.zip
specify preset resolve spec-template                  # shows the preset in effect
```

From a kit clone instead: `specify preset add --dev <kit>/presets/spec-kit`.

Spec Kit seeds `.specify/memory/constitution.md` once, from the constitution template in effect at that time. If the project already has one, run the `constitution` command to update it from the new template.
