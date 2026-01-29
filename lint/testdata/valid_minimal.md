# Valid Minimal Spec

This is a minimal valid Simplex specification with all required landmarks.

FUNCTION: add(a, b) → sum

RULES:
  - if both inputs are numbers, return their sum
  - if either input is not a number, fail

DONE_WHEN:
  - result is the arithmetic sum of a and b

EXAMPLES:
  (2, 3) → 5
  (0, 0) → 0
  (-1, 1) → 0
  (100, 200) → 300

ERRORS:
  - non-numeric input → fail with "input must be numeric"
  - any unhandled condition → fail with descriptive message
