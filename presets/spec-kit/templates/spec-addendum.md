
## Non-Functional Requirements _(mandatory)_

<!-- Number them NFR-001, NFR-002, ... Each must be measurable. Write "None beyond the constitution" only if true. -->

- **NFR-001**: [Performance, e.g. "p95 response under 500 ms at 50 requests/s"]
- **NFR-002**: [Availability or recovery, e.g. "recovers from a dependency outage without data loss"]
- **NFR-003**: [Accessibility, observability, or operability, e.g. "WCAG 2.2 AA", "every failure is logged with a request ID"]

## Security & Privacy _(mandatory)_

- **Access**: [Who can use this, and which role or permission each action needs]
- **Threats**: [What could go wrong: abuse, injection, data exposure; and the control for each]
- **Secrets**: [Credentials involved, where they live (vault, managed identity), who can read them]
- **Untrusted input**: [Inputs from users, files, other systems or AI models, and how each is validated]

## Data Handling _(include if the feature stores, moves or shows data)_

- **Data**: [Entities and fields; mark personal or confidential ones]
- **Retention**: [How long each is kept, and how it is deleted]
- **Location**: [Where it is stored and processed; any residency rule]
- **Sharing**: [Which systems or people receive it]

## Traceability

- Requirement IDs (FR-###, SC-###, NFR-###) go into the backlog item, the PR body ("Requirements:"), test names and release notes.
- Every `[NEEDS CLARIFICATION: ...]` left after `clarify` becomes a backlog item labelled `needs-decision` for the spec's code owners (the kit's `spec-decisions` workflow opens and closes them). Build waits until they are decided.
