---
applyTo: "**/*.bicep"
stack: [bicep]
---

# Bicep

- One module per resource type; parameters typed, with `@description` and safe defaults.
- Managed identity and RBAC over keys; no secrets in parameters or outputs (`@secure()` when unavoidable).
- Private endpoints and disabled public access for data services unless the reason is written down.
- Tag every resource; follow the project's naming pattern.
- `az bicep build` must pass with no warnings.
