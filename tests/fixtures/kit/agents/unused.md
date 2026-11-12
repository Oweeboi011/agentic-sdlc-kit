---
name: unused
description: Enabled by no project in the fixture.
stage: 6
triggers: [manual]
tools: [read]
permissions: {contents: read}
human_gate: {mode: propose, reviewer: on-call}
evidence: {kind: issue, label: "agent:unused", trigger: manual}
---
Never rendered.
