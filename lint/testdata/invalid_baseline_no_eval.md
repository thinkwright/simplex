# Invalid: BASELINE without EVAL

This specification has BASELINE but is missing the required EVAL landmark.
EVAL is conditionally required when BASELINE is present.

FUNCTION: migrate_database(config) → MigrationResult

BASELINE:
  reference: "PostgreSQL 12, schema v2.1"
  preserve:
    - existing queries continue to work
    - data integrity maintained
  evolve:
    - upgrade to PostgreSQL 15
    - add new indexes for performance

RULES:
  - apply schema migrations in order
  - preserve backward compatibility
  - add new indexes without locking

DONE_WHEN:
  - all migrations applied successfully
  - existing queries verified
  - new indexes created

EXAMPLES:
  (valid_config) → { success: true, migrations_applied: 5 }
  (invalid_config) → { error: "invalid configuration" }

ERRORS:
  - migration failed → fail with "migration {n} failed: {reason}"
  - any unhandled condition → fail with descriptive message

# Missing EVAL landmark - this should fail validation with E060
