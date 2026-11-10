---
name: story-refinement
description: "Turn a rough issue into a ready story: goal, acceptance criteria, scope, test notes, estimate. Use for backlog refinement."
---

# Story refinement

Write the proposal in this shape:

- **Goal:** who benefits and what changes for them, in one sentence.
- **Acceptance criteria:** 3–7 testable statements (Given/When/Then or plain checks). Each maps to at least one test.
- **Out of scope:** what this story will not do.
- **Test notes:** which layers (unit, integration, e2e) and any data or environment needed.
- **Estimate:** S (≤1 day), M (≤3 days), L (split it).
- **Open questions:** anything a human must decide.

Rules: one story fits one PR; if it is L, propose child issues. Don't invent requirements: ask.
