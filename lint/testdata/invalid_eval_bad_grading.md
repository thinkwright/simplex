# Invalid: EVAL with invalid grading type

This specification has EVAL with an unrecognized grading type.
Grading must be one of: code, model, outcome.

FUNCTION: improve_code_quality(source) → ImprovedCode

BASELINE:
  reference: "legacy codebase"
  preserve:
    - existing functionality
    - API contracts
  evolve:
    - improve test coverage
    - add type annotations

RULES:
  - maintain all existing behavior
  - add type hints to functions
  - add missing unit tests

DONE_WHEN:
  - all tests pass
  - type coverage increased
  - behavior unchanged

EXAMPLES:
  (untyped_function) → typed_function
  (untested_module) → module_with_tests
  (legacy_code) → improved_code

ERRORS:
  - any unhandled condition → fail with descriptive message

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: fuzzy          # Invalid - should be code, model, or outcome
