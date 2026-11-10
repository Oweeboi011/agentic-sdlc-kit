---
applyTo: "**/*.py"
stack: [python]
---

# Python

- Python 3.11+. Type hints on public functions. `ruff` for lint and format.
- Async for I/O; no blocking calls in async paths; use `httpx`, not `requests`.
- Raise specific exceptions; map them to HTTP status codes in one place.
- Configuration from environment variables; credentials from managed identity, never from code.
- Tests with `pytest`; mock at the process boundary, not internal modules.
