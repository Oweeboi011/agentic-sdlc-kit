---
applyTo: "**"
---

# General

- Scoped changes; root-cause fixes; reuse before creating; delete dead code.
- One responsibility per module; dependencies point inward; no import cycles.
- Never log or commit secrets, tokens or personal data.
- Comments only for non-obvious intent, at most two lines.
- Run the project gate (see `AGENTS.md`) before handing off.
