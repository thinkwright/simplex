# Valid v0.6 Traceability

This fixture uses the optional version, identifier, example-kind, and COVERS features.

SIMPLEX: 0.6

CONSTRAINT: numeric_output
  - [C1] successful output is numeric

FUNCTION: add(a, b) → number

RULES:
  - [R1] return the arithmetic sum of numeric inputs

DONE_WHEN:
  - [D1] the result equals a + b

EXAMPLES:
  - [E1] value: (2, 3) → 5
  - [E2] error: ("x", 3) → fail with "input must be numeric"

ERRORS:
  - [X1] non-numeric input → fail with "input must be numeric"
  - any unhandled condition → fail with descriptive message

COVERS:
  - E1 → R1, D1, C1
  - E2 → X1
