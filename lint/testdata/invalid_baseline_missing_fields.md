# Invalid: BASELINE missing required fields

This specification has BASELINE but is missing the required 'evolve' field.
BASELINE requires: reference, preserve, and evolve.

FUNCTION: refactor_api(endpoints) → RefactoredAPI

BASELINE:
  reference: "REST API v1"
  preserve:
    - existing endpoint paths unchanged
    - response formats maintained
  # Missing 'evolve' field - should fail with E052

RULES:
  - maintain backward compatibility
  - improve internal structure

DONE_WHEN:
  - all endpoints respond correctly
  - existing clients unaffected

EXAMPLES:
  (current_endpoints) → refactored_endpoints
  (empty_list) → empty_list

ERRORS:
  - any unhandled condition → fail with descriptive message

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code
