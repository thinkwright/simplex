# Invalid: EVAL with invalid threshold notation

This specification has EVAL with incorrectly formatted thresholds.
Thresholds must use pass^k or pass@k notation where k is a positive integer.

FUNCTION: upgrade_service(config) → ServiceResult

BASELINE:
  reference: "service v1.0"
  preserve:
    - health check endpoint
    - metrics endpoint
  evolve:
    - add new API version
    - improve performance

RULES:
  - maintain existing endpoints
  - add new versioned API

DONE_WHEN:
  - all endpoints respond
  - new API available

EXAMPLES:
  (valid_config) → { success: true }
  (legacy_request) → { handled: true }
  (new_api_request) → { version: "v2" }

ERRORS:
  - any unhandled condition → fail with descriptive message

EVAL:
  preserve: pass3        # Invalid - should be pass^3, missing caret
  evolve: pass@five      # Invalid - should be pass@5, not a number
  grading: code
