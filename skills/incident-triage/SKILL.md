---
name: incident-triage
description: "Triage a production incident: impact, timeline, evidence from logs and metrics, likely cause, proposed mitigation. Use when an alert fires."
---

# Incident triage

1. **Impact:** which users or features, since when, how many requests or errors. Set severity (SEV1 outage … SEV3 degraded).
2. **Timeline:** alert time, last deploys and config changes before it (deploy workflow runs, Environment history).
3. **Evidence:** query logs and metrics (KQL): error rate, top exceptions, latency, dependency failures, before vs after the start. Paste the queries.
4. **Cause:** the most likely cause with confidence (high/medium/low) and what would confirm it.
5. **Mitigation:** smallest safe action first: roll back the last deploy, turn off a flag, scale out. Give exact steps and who must approve.
6. **Follow-up:** the test, alert or guardrail that would have caught it.

Read-only: propose actions; never execute them.
