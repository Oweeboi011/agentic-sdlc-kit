---
name: release-runbook
description: "Prepare a release: notes from merged PRs, risks, migrations, verification and a rollback plan. Use before promoting to production or when rolling back."
---

# Release runbook

## Notes

1. List PRs merged since the last release tag; group them as Features, Fixes, Infrastructure, Dependencies.
2. Call out breaking changes, data migrations, new configuration or secrets, and feature flags.

## Risk and verification

- Risk per change (low/medium/high) and why.
- Smoke checks after deploy: health endpoint, one key user journey, error rate and latency against the last release.

## Rollback plan

- **App:** redeploy the previous image tag or reactivate the previous revision; name the exact tag.
- **Data:** say whether migrations are backward compatible; if not, the restore point.
- **Config:** previous values of any changed settings.
- Who decides, and the signal that triggers rollback (for example error rate above baseline for 10 minutes).
