---
name: test-patterns
description: "Which test layer a change needs and how to write tests that survive refactors. Use when adding or reviewing tests."
---

# Test patterns

| Layer | Tests | Mock at |
|---|---|---|
| unit | pure logic, one module | nothing, or a fake passed in |
| integration | an API route or component with its real collaborators | the process boundary (HTTP, database, cloud SDK) |
| contract | shapes shared across a boundary (API schema, events, pricing tables) | nothing: compare both sides |
| e2e | a user journey through the built app | external services only |

- Test behaviour through public interfaces; a test should survive an internal refactor.
- One behaviour per test; the name states it ("rejects an expired token").
- Prefer real objects and in-memory fakes over mocks of internal collaborators.
- Each bug fix adds the test that would have caught it.
- Keep tests deterministic: no sleeps, fixed clocks and seeds, no network in unit tests.
- Follow the project's own testing guide for folder layout and markers.
