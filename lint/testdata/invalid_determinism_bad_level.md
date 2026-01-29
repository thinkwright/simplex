# Invalid Determinism - Bad Level

This specification has an invalid DETERMINISM level.
Expected error: E070 "DETERMINISM level must be strict, structural, or semantic"

FUNCTION: generate_id() → string

DETERMINISM:
  level: fuzzy
  seed: none

RULES:
  - generate a unique identifier
  - format as UUID v4

DONE_WHEN:
  - identifier is returned
  - format is valid UUID

EXAMPLES:
  () → "550e8400-e29b-41d4-a716-446655440000"

ERRORS:
  - any unhandled condition → fail with descriptive message
