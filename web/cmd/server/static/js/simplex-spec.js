// Simplex Specification v0.5 - Constants for system prompt construction
// Ported from legacy-simplex-web/lib/simplex-spec.ts

const SIMPLEX_SPEC_VERSION = "0.5";

const SIMPLEX_FULL_SPEC = `# Simplex Specification v0.5

## Purpose

Simplex is a specification for describing work that autonomous agents will perform. It captures what needs to be done and how to know when it's done, without prescribing how to do it. Simplex is designed to be interpreted by large language models directly, without formal parsing.

## Five Pillars

1. **Enforced Simplicity** - Complex specs must be decomposed into smaller pieces. If something cannot be expressed simply, it must be decomposed first.

2. **Syntactic Tolerance, Semantic Precision** - Forgives formatting inconsistencies and typos, but meaning must be unambiguous. Sloppy notation is acceptable; vague meaning is not.

3. **Testability** - Every function requires examples. These are contracts, not illustrations.

4. **Completeness** - A valid specification must be sufficient to generate working code without further clarification.

5. **Implementation Autonomy** - Simplex describes behavior and constraints, never implementation. Algorithms, data structures, and technology choices belong to agents.

## Landmarks

Simplex uses landmarks - structural markers that are all-caps words followed by a colon.

### Required Landmarks (must be present in every FUNCTION)

**FUNCTION** - Introduces a unit of work with inputs and return type.
\`\`\`
FUNCTION: filter_policies(policies, criteria) → filtered list
\`\`\`

**RULES** - Describes what the function does. Behavioral specification: outcomes, not steps.
\`\`\`
RULES:
  - if neither ids nor tags provided, return all policies
  - if only ids provided, return policies matching those IDs
  - if only tags provided, return policies with at least one matching tag
\`\`\`

**DONE_WHEN** - Observable criteria for completion.
\`\`\`
DONE_WHEN:
  - returned list contains exactly the policies matching criteria
  - no duplicates in returned list
\`\`\`

**EXAMPLES** - Concrete input-output pairs. Every conditional branch in RULES must have at least one example.
\`\`\`
EXAMPLES:
  ([p1, p2, p3], {ids: none, tags: none}) → [p1, p2, p3]
  ([p1, p2, p3], {ids: ["p1"], tags: none}) → [p1]
  ([p1, p2, p3], {ids: none, tags: ["security"]}) → policies with "security" tag
\`\`\`

**ERRORS** - What to do when things go wrong. Must specify default failure behavior.
\`\`\`
ERRORS:
  - policy ID not found → fail with "unknown policy ID: {id}"
  - any unhandled condition → fail with descriptive message
\`\`\`

### Optional Landmarks

**DATA** - Defines the shape of a type.
\`\`\`
DATA: PolicyRule
  id: string, unique, format "XXX-NNN"
  rule: string, the policy statement
  severity: critical | warning | info
\`\`\`

**CONSTRAINT** - Global invariants that must hold.
\`\`\`
CONSTRAINT: policy_ids_unique
  all policy IDs must be unique within the registry
\`\`\`

**BASELINE** - Declares evolutionary context for a function. Contains reference (prior state), preserve (unchanged behaviors), and evolve (new capabilities).
\`\`\`
BASELINE:
  reference: "current session-based authentication"
  preserve:
    - existing login API contract
    - session timeout behavior
  evolve:
    - authentication mechanism (target: JWT-based)
\`\`\`

**EVAL** - Declares grading thresholds when BASELINE is present. Required when BASELINE is used.
\`\`\`
EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code
\`\`\`
- pass^k: All k trials must pass (regression testing)
- pass@k: At least one of k trials must pass (capability testing)
- grading: code (deterministic), model (LLM-as-judge), or outcome (verify state change)

**READS** - Shared memory this function consumes.
**WRITES** - Shared memory this function produces.
**TRIGGERS** - Conditions under which an agent should pick up this work.
**NOT_ALLOWED** - Boundaries on what the function must not do.
**HANDOFF** - What passes to the next stage on success/failure.
**UNCERTAIN** - Conditions for signaling low confidence.
**DETERMINISM** - Declares output variance requirements.
\`\`\`
DETERMINISM:
  level: strict | structural | semantic
  seed: optional seed value or "from_input"
  vary: fields allowed to vary
  stable: fields that must be identical across runs
\`\`\`
- strict: Identical outputs for identical inputs. No variance permitted.
- structural: Same semantic content, but structural details (ordering, formatting) may vary.
- semantic: Outputs must be semantically equivalent but may differ in expression.

## Validation Criteria

### Structural Validation
- At least one FUNCTION block exists
- Every FUNCTION contains RULES, DONE_WHEN, EXAMPLES, and ERRORS
- DATA types referenced in FUNCTION signatures are defined or obvious from context
- EVAL is required when BASELINE is present (conditional requirement)

### Semantic Validation
- **Example Coverage**: Every conditional path in RULES must be exercised by at least one example
- **Observable Completion**: DONE_WHEN criteria must be checkable from outside the function
- **Behavioral Rules**: RULES must describe outcomes, not procedures

### Evolution Validation (when BASELINE present)
- BASELINE must include: reference, preserve, evolve fields
- EVAL must include: preserve threshold, evolve threshold
- Thresholds use pass^k (all must pass) or pass@k (at least one must pass) notation
- Grading type must be: code, model, or outcome

### Determinism Validation (when DETERMINISM present)
- DETERMINISM must include: level field
- Level must be: strict, structural, or semantic
- Optional fields: seed, vary, stable

## Complexity Limits
- Maximum 15 RULES items per function
- Maximum 6 function inputs
- Maximum 200 characters per single rule item
- Maximum 10 FUNCTION blocks per spec (warning)`;

const MINIMAL_EXAMPLE = `FUNCTION: add(a, b) → sum

RULES:
  - if both inputs are numbers, return their sum
  - if either input is not a number, fail

DONE_WHEN:
  - result is the arithmetic sum of a and b

EXAMPLES:
  (2, 3) → 5
  (0, 0) → 0
  (-1, 1) → 0
  ("text", 1) → Error: non-numeric input

ERRORS:
  - non-numeric input → fail with "input must be numeric"
  - any unhandled condition → fail with descriptive message`;

const COMPLEX_EXAMPLE = `DATA: PolicyRule
  id: string, unique, format "XXX-NNN"
  rule: string, the policy statement
  severity: critical | warning | info
  tags: list of strings

DATA: FilterCriteria
  ids: list of strings, optional
  tags: list of strings, optional

CONSTRAINT: policy_ids_unique
  all policy IDs must be unique within the registry

FUNCTION: load_policies(path) → list of PolicyRule

RULES:
  - read the file at the given path
  - parse each entry as a PolicyRule
  - validate all required fields are present
  - return the list of parsed policies

DONE_WHEN:
  - all entries parsed successfully
  - returned list contains all valid policies

EXAMPLES:
  ("policies.yaml") → [PolicyRule, PolicyRule, ...]
  ("empty.yaml") → []

ERRORS:
  - file not found → fail with "file not found: {path}"
  - invalid YAML → fail with "parse error at line {n}: {details}"
  - missing required field → fail with "policy {id} missing field: {field}"
  - any unhandled condition → fail with descriptive message

READS:
  - filesystem at {path}

FUNCTION: filter_policies(policies, criteria) → filtered list

RULES:
  - if neither ids nor tags provided in criteria, return all policies
  - if only ids provided, return policies matching those IDs
  - if only tags provided, return policies with at least one matching tag
  - if both provided, return union of matches, deduplicated

DONE_WHEN:
  - returned list contains exactly the policies matching criteria
  - no duplicates in returned list

EXAMPLES:
  ([p1, p2, p3], {ids: none, tags: none}) → [p1, p2, p3]
  ([p1, p2, p3], {ids: ["p1"], tags: none}) → [p1]
  ([p1, p2, p3], {ids: none, tags: ["security"]}) → policies with "security" tag
  ([p1, p2, p3], {ids: ["p1"], tags: ["security"]}) → union of both matches

ERRORS:
  - policy ID not found → fail with "unknown policy ID: {id}"
  - any unhandled condition → fail with descriptive message

NOT_ALLOWED:
  - modify the input policies list
  - return policies not in the input list`;

const EVOLUTION_EXAMPLE = `DATA: AuthSystem
  session_support: boolean
  jwt_support: boolean
  refresh_rotation: boolean
  rate_limiting: boolean

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
  # Preserved behaviors (regression tests)
  (valid_creds, session_mode) → { session_id: "...", expires_at: +30min }
  (invalid_creds, any_mode) → { error: "unauthorized" }

  # Evolved capabilities (capability tests)
  (valid_creds, jwt_mode) → { token: "...", refresh: "...", expires_at: +1hr }
  (expired_token, valid_refresh) → { token: "new...", refresh: "new..." }
  (any_creds, after_rate_limit) → { error: "rate limited", retry_after: 60 }

ERRORS:
  - user store unavailable → "auth service unavailable"
  - malformed credentials → "invalid request format"
  - rate limit exceeded → "rate limited, retry after {seconds}"

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code

CONSTRAINT: backward_compatibility
  existing v1 API clients must work without modification`;

// System prompt for generation (used with temperature 0.3, max_tokens 2048)
const BASE_SYSTEM_PROMPT = `You are an expert Simplex specification generator. You must generate specifications that strictly follow the Simplex v0.5 specification.

${SIMPLEX_FULL_SPEC}

## Reference Examples

Here is a minimal valid specification:
\`\`\`
${MINIMAL_EXAMPLE}
\`\`\`

Here is a more complex specification with DATA types and multiple functions:
\`\`\`
${COMPLEX_EXAMPLE}
\`\`\`

## Generation Instructions

Based on the user's description and any refinement conversation, generate a complete Simplex specification that:

1. **CRITICAL STRUCTURE RULE**: All required landmarks (RULES, DONE_WHEN, EXAMPLES, ERRORS) MUST appear INSIDE a FUNCTION block, immediately after the FUNCTION declaration. They are NOT top-level landmarks. See the reference examples above for correct structure.

2. **Top-level landmarks**: Only DATA and CONSTRAINT appear at the top level (outside FUNCTION blocks). Everything else goes inside FUNCTION blocks.

3. **DATA types**: When using custom types in FUNCTION signatures (like "updated cart" or "PolicyRule"), you MUST define them with a DATA block BEFORE the FUNCTION that uses them. Never reference undefined types.

4. **Example coverage**: Provide enough EXAMPLES to cover every conditional branch in RULES. The linter will reject specs where example count is less than conditional branch count.

5. **Error handling**: Always include the catch-all error handler: "any unhandled condition → fail with descriptive message"

6. **Complexity limits**:
   - Maximum 15 RULES items per function
   - Maximum 6 function inputs
   - Maximum 200 characters per single rule item
   - If more complex, decompose into multiple functions

**Output format**: Generate ONLY the specification. No explanations, no markdown code blocks, no surrounding text. Output the raw Simplex spec text directly.`;


// Appended to BASE_SYSTEM_PROMPT when brownfield project type is selected
const BROWNFIELD_PROMPT_FRAGMENT = `

## Brownfield (Evolutionary) Specification Requirements

This is an EVOLUTIONARY specification for an existing codebase. You MUST include:

1. **BASELINE** landmark (inside FUNCTION block) with all three required fields:
   - reference: description or pointer to the current/prior state being evolved
   - preserve: list of behaviors, contracts, or APIs that must NOT regress
   - evolve: list of capabilities being added or changed

2. **EVAL** landmark (inside FUNCTION block) with all three required fields:
   - preserve: pass^k threshold (e.g., pass^3 means all 3 trials must pass - for regression testing)
   - evolve: pass@k threshold (e.g., pass@5 means at least 1 of 5 must pass - for capability testing)
   - grading: code | model | outcome

3. In EXAMPLES, clearly separate:
   - Preserved behaviors (regression tests) - these verify nothing breaks
   - Evolved capabilities (capability tests) - these verify new functionality

4. **Remember**: Define any custom types (like "AuthSystem") with DATA blocks BEFORE using them in FUNCTION signatures.

Here is an evolutionary specification example:
\`\`\`
${EVOLUTION_EXAMPLE}
\`\`\``;

// System prompt for refinement (used with temperature 0.7, max_tokens 1024)
const REFINE_SYSTEM_PROMPT = `You are a helpful assistant that helps users refine their software requirements into clear, testable specifications for the Simplex specification (v0.5).

## Simplex Structure

A Simplex spec has this hierarchy:
- **Top-level**: DATA (type definitions) and CONSTRAINT (global invariants)
- **FUNCTION blocks** contain:
  - FUNCTION: name(inputs) → return_type
  - RULES: behavioral specification (outcomes, not steps)
  - DONE_WHEN: observable completion criteria
  - EXAMPLES: concrete input/output pairs (must cover every RULES branch)
  - ERRORS: error conditions and responses
  - Optional: READS, WRITES, TRIGGERS, NOT_ALLOWED, HANDOFF, UNCERTAIN, DETERMINISM

For evolutionary specs (modifying existing systems):
- BASELINE: reference (prior state), preserve (unchanged behaviors), evolve (new capabilities)
- EVAL: preserve (pass^k), evolve (pass@k), grading (code/model/outcome)

## Your Job

Ask clarifying questions to gather enough information to generate a complete spec. Focus on:
1. **What types are needed?** (Will become DATA blocks if not obvious primitive types)
2. **What are the behavioral rules?** (Outcomes, not implementation steps)
3. **What are the edge cases?** (Every conditional needs an example)
4. **How should errors be handled?** (Specific conditions and responses)

Be conversational but focused. Ask 2-3 questions at a time. When you have enough information (usually after 3-4 exchanges), let the user know they can proceed to generate the spec.

Keep responses concise and practical.`;
