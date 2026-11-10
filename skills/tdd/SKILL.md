---
name: tdd
description: "Test-driven development in vertical slices: one failing test, the smallest change that passes, repeat. Use for features and bug fixes."
---

# Test-driven development

Tests verify behaviour through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

## Vertical slices, not horizontal

Do **not** write all tests first and then all code: bulk tests describe imagined behaviour and test the shape of things. Work one slice at a time:

```
RED -> GREEN: test1 -> impl1
RED -> GREEN: test2 -> impl2
```

## Loop

1. **Plan:** agree the interface and the few behaviours that matter most. You cannot test everything; focus on critical paths and complex logic.
2. **Tracer bullet:** one test for the first behaviour; watch it fail; write the minimal code to pass.
3. **Increment:** next test, minimal code, repeat. Don't anticipate future tests.
4. **Refactor** only when green: remove duplication, deepen modules (small interface, deep implementation), rerun tests after each step.

## Checklist per cycle

- [ ] Test describes behaviour, not implementation
- [ ] Test uses the public interface only
- [ ] Test would survive an internal refactor
- [ ] Code is minimal for this test; no speculative features
