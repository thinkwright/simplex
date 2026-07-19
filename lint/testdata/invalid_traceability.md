# Invalid v0.6 Traceability

The COVERS target does not resolve.

SIMPLEX: 0.6

FUNCTION: add(a, b) → number

RULES:
  - [R1] return the arithmetic sum

DONE_WHEN:
  - [D1] the result equals a + b

EXAMPLES:
  - [E1] value: (2, 3) → 5

ERRORS:
  - any unhandled condition → fail with descriptive message

COVERS:
  - E1 → R1, D1, missing
