# Valid Output Schema

A valid Simplex specification demonstrating DATA as required output schema.
Function return type references DATA block, and all examples conform to schema.

DATA: ApiResponse
  status: success | error, required
  data: any, present when status=success
  message: string, present when status=error
  timestamp: ISO8601 datetime, required
  request_id: UUID, required

FUNCTION: process_request(input) → ApiResponse

RULES:
  - validate input format
  - if valid, process and return success response with data
  - if invalid, return error response with message
  - always include timestamp and request_id

DONE_WHEN:
  - response matches ApiResponse schema exactly
  - no extra fields in response
  - all required fields present

EXAMPLES:
  (valid_input) → { status: success, data: {...}, timestamp: "2024-01-01T00:00:00Z", request_id: "abc-123" }
  (invalid_input) → { status: error, message: "invalid format", timestamp: "2024-01-01T00:00:00Z", request_id: "abc-124" }
  (empty_input) → { status: error, message: "input required", timestamp: "2024-01-01T00:00:00Z", request_id: "abc-125" }

ERRORS:
  - null input → fail with "input cannot be null"
  - any unhandled condition → fail with descriptive message

CONSTRAINT: output_schema_strict
  output must conform exactly to ApiResponse schema
  no additional fields allowed
  all required fields must be present
