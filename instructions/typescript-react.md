---
applyTo: "**/*.ts,**/*.tsx"
stack: [typescript-react]
---

# TypeScript and React

- Strict TypeScript; no `any` (narrow `unknown`).
- Network calls only through the project's API client module; no inline `fetch` in components.
- Components small and typed; split when they grow past about 200 lines.
- No synchronous `setState` inside a `useEffect` body.
- Tests: Vitest + Testing Library for units and components, Playwright for user journeys.
