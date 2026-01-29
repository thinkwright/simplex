# Invalid Output Schema - Missing Required Field

This specification has examples that don't conform to the output schema.
Expected error: E081 "example output missing required field 'timestamp'"

DATA: ApiResponse
  status: success | error, required
  data: any, present when status=success
  timestamp: ISO8601 datetime, required

FUNCTION: process_request(input) → ApiResponse

RULES:
  - validate input and return appropriate response
  - always include timestamp in response

DONE_WHEN:
  - response matches ApiResponse schema

EXAMPLES:
  # This example is missing the required 'timestamp' field
  (valid_input) → { status: success, data: {...} }
  (invalid_input) → { status: error, timestamp: "2024-01-01T00:00:00Z" }

ERRORS:
  - any unhandled condition → fail with descriptive message
