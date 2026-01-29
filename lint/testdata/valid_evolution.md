# Valid Evolution Spec

A valid Simplex specification demonstrating BASELINE and EVAL landmarks
for evolutionary specifications.

FUNCTION: modernize_authentication(config) → AuthSystem

BASELINE:
  reference: "session-based auth, commit abc123"
  preserve:
    - POST /login returns { session_id, expires_at }
    - session timeout is 30 minutes
    - existing client SDKs continue to work
  evolve:
    - add JWT token issuance alongside sessions
    - implement refresh token rotation
    - add rate limiting on auth endpoints

RULES:
  - authenticate user credentials against user store
  - issue JWT token with configurable expiration
  - issue refresh token that rotates on each use
  - maintain session-based auth for backward compatibility
  - rate limit failed attempts per IP address

DONE_WHEN:
  - valid credentials produce both session and JWT
  - refresh tokens rotate correctly
  - rate limiting activates after threshold
  - existing session-based clients unaffected

EXAMPLES:
  # Preserved behaviors (regression)
  (valid_creds, session_mode) → { session_id: "...", expires_at: +30min }
  (invalid_creds, any_mode) → { error: "unauthorized" }

  # Evolved capabilities
  (valid_creds, jwt_mode) → { token: "...", refresh: "...", expires_at: +1hr }
  (expired_token, valid_refresh) → { token: "new...", refresh: "new..." }
  (any_creds, after_rate_limit) → { error: "rate limited", retry_after: 60 }

ERRORS:
  - user store unavailable → fail with "auth service unavailable"
  - malformed credentials → fail with "invalid request format"
  - any unhandled condition → fail with descriptive message

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code
