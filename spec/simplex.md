# Simplex

A workflow specification for autonomous agents.

Version 0.6

---

## Purpose

Simplex is a specification for describing work that autonomous agents will perform. It captures what needs to be done and how to know when it's done, without prescribing how to do it. It is designed for direct interpretation by large language models.

The motivation is practical. When agents work autonomously for extended periods, they need instructions that are complete enough to act on without clarification, yet flexible enough to allow implementation choices. Simplex adds repeatable structure to prose while leaving algorithms, data structures, and technology choices unspecified.

---

## Pillars

Five pillars guide Simplex.

**Enforced simplicity.** Simplex refuses to support constructs that would allow specifications to become unwieldy. If something cannot be expressed simply, it must be decomposed into smaller pieces first. This is a feature, not a limitation. Complexity that cannot be decomposed is complexity that is not yet understood.

*Note: Enforcement happens through tooling, not the specification itself. The current Simplex linter enforces limits on RULES items and function inputs, and warns about long rules and large function counts. The specification defines the broader simplicity principle; tooling enforces only its documented checks. See the Linter Specification section.*

**Syntactic tolerance, semantic precision.** Agent interpretation may tolerate formatting inconsistencies and minor notational variations, while the intended meaning must remain unambiguous. Tooling supports only its documented tolerance; for example, a misspelled required landmark can still be reported as missing. If an agent would have to guess the author's intent, the specification is invalid.

*Note: Authors and reviewers assess semantic precision through example coverage and interpretation review. If examples do not exercise every branch of the rules, or if examples could be satisfied by multiple conflicting interpretations, the specification is ambiguous and invalid. The current linter uses a count-based branch/example heuristic; it does not prove semantic coverage or interpretation uniqueness. See Validation Criteria.*

**Testability.** Every function requires examples. These are not illustrations; they are contracts. The examples define what correct output looks like for given inputs. An agent's work is not complete until its output is consistent with the examples.

**Completeness.** A valid specification must be sufficient to generate working code without further clarification. This is what distinguishes Simplex from a prompting approach. There is no back-and-forth, no "what did you mean by X?" The spec must stand alone.

**Implementation autonomy.** Simplex describes behavior and constraints, never implementation. Algorithms, data structures, and technology choices belong to agents. If a spec needs persistent storage, it says so. Whether that becomes a graph database, file system, or something else is the agent's concern. The spec neither prescribes nor cares.

---

## Interpretation Model

Simplex does not require a formal grammar, parser, AST, or compilation step for agent interpretation. Agents read specifications as semi-structured text and extract meaning directly. Tooling may use tolerant parsers and intermediate representations to inspect that structure.

This is intentional. A formal grammar would contradict the principle of syntactic tolerance. It would also add complexity and create failure modes. Since Simplex exists for LLM interpretation, it should be native to how LLMs work.

Instead of grammar rules, Simplex uses landmarks. Landmarks are structural markers that agents recognize and orient around. They are all-caps words followed by a colon. Content under a landmark continues until the next landmark or the end of the document.

Agents scan for landmarks, extract the content associated with each, and build understanding from there. Agents ignore unrecognized landmarks rather than rejecting the document, which provides forward compatibility as Simplex evolves. The current linter reports unrecognized landmarks as warnings.

---

## Landmarks

Simplex defines eighteen landmarks. Six describe structure. Twelve describe functions.

### Structural Landmarks

**SIMPLEX** optionally declares the language version used by a document. The declaration has a
single `major.minor` value and, when present, must appear only once.

```
SIMPLEX: 0.6
```

Documents without a SIMPLEX declaration remain valid for backward compatibility. Tooling must
report a declared version it does not support rather than claiming that all applicable checks
passed. The declaration selects specification semantics; it is independent from the version of a
particular linter binary.

**DATA** defines the shape of a type. It names a concept and lists its fields with descriptions and constraints. DATA blocks help agents understand what they are working with, but they are optional. If a function's inputs and outputs are clear from context, explicit DATA definitions are unnecessary.

```
DATA: PolicyRule
  id: string, unique, format "XXX-NNN"
  rule: string, the policy statement
  severity: critical | warning | info
  tags: list of strings
  example_violation: string, optional
  example_fix: string, optional
```

**DATA as Output Schema.** When a function's return type references a DATA block, that DATA block acts as a **required output schema**. Agents must produce outputs that conform to the schema—no missing required fields, no unexpected fields, no type mismatches. This significantly reduces output variance.

```
DATA: Response
  status: success | error
  data: any, present when status=success
  message: string, present when status=error
  timestamp: ISO8601 datetime, required
  request_id: UUID, required

FUNCTION: process_request(input) → Response
```

When the return type explicitly references a DATA block, the function's output is constrained to match that schema exactly. Agents must not improvise output structure.

DATA blocks can specify:
- **required fields**: must always be present (default)
- **optional fields**: marked with `optional`, may be absent
- **conditional fields**: present under specified conditions
- **field types**: primitives, enums, references to other DATA blocks, or `any`
- **format constraints**: patterns, ranges, or explicit value sets

```
DATA: StrictOutput
  result: number, required, range 0-100
  confidence: high | medium | low, required
  details: list of Finding, optional
  metadata: any, not allowed

DATA: Finding
  line: positive integer, required
  message: string, required, max 200 chars
  severity: error | warning | info, required
```

The `not allowed` annotation explicitly prohibits a field, preventing agents from adding unexpected metadata or debug information to outputs.

**CONSTRAINT** states an invariant that must hold. Unlike function-specific rules, constraints apply broadly. They describe conditions that should never be violated, regardless of which function is executing.

Constraints serve as **behavioral anchors**—they reduce implementation variance by specifying what must remain true regardless of how an agent chooses to implement the work. Well-crafted constraints narrow the space of valid implementations without prescribing a specific approach.

```
CONSTRAINT: policy_ids_must_exist
  any policy ID referenced anywhere must exist in the registry
```

Constraints can specify:
- **State invariants**: conditions that must hold before, during, and after execution
- **Output guarantees**: properties that all outputs must satisfy
- **Boundary conditions**: limits on what outputs may contain

```
CONSTRAINT: output_format_stable
  output structure must match the DATA schema exactly
  no additional fields may be added
  no fields may be omitted unless marked optional in DATA

CONSTRAINT: idempotency
  calling the function twice with identical inputs produces identical outputs
  no cumulative side effects from repeated calls
```

The more precise your constraints, the less variance in agent implementations. Vague constraints like "output should be reasonable" provide no anchoring. Specific constraints like "output must be valid JSON matching the Response schema" anchor behavior effectively.

**FUNCTION** introduces a unit of work. It names an operation, lists its inputs, and declares its return type. The function block contains nested landmarks that specify behavior, completion criteria, and test cases.

```
FUNCTION: filter_policies(policies, ids, tags) → filtered list
```

**BASELINE** declares evolutionary context for a function. It establishes what currently exists, what must be preserved during evolution, and what is being evolved. BASELINE is optional; when absent, the function is treated as greenfield (building something new rather than modifying something existing).

```
BASELINE:
  reference: "current session-based authentication"
  preserve:
    - existing login API contract
    - session timeout behavior (30 minutes)
    - backward compatibility for v1 clients
  evolve:
    - authentication mechanism (target: JWT-based)
    - token refresh (target: rotation on each use)
```

BASELINE contains three required fields when present:
- **reference**: A description or pointer to the prior state being evolved from. Can be prose or a concrete reference (commit hash, version tag).
- **preserve**: Behaviors, contracts, or properties that must remain unchanged. These become regression tests.
- **evolve**: Capabilities being added or changed. These represent forward progress.

BASELINE differs from CONSTRAINT. A constraint is a timeless invariant ("all tokens must be signed"). A preserved behavior is relative to a reference point ("the login API response shape was X before, keep it X"). Both can coexist in a specification.

**EVAL** declares how to measure success for a function's examples. It specifies grading approaches and thresholds, particularly distinguishing regression tests (must always pass) from capability tests (measure progress). EVAL is required when BASELINE is present; optional otherwise.

```
EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code
```

EVAL contains three fields:
- **preserve**: Threshold for preserved behaviors using `pass^k` notation (all k trials must pass). Required when BASELINE present.
- **evolve**: Threshold for evolved capabilities using `pass@k` notation (at least 1 of k attempts must succeed). Required when BASELINE present.
- **grading**: How examples are evaluated: `code` (deterministic comparison, default), `model` (LLM-as-judge for subjective outputs), or `outcome` (verify actual state change). Optional, defaults to `code`.

The threshold notation:
- `pass^k` means all k trials must pass. Used for regression tests where consistency is required.
- `pass@k` means at least 1 of k trials must pass. Used for capability tests where progress is being measured.

When BASELINE is absent and EVAL is omitted, examples are treated as traditional test cases with implicit `code` grading and `pass^1` threshold.

### Function Landmarks

These landmarks appear within a FUNCTION block.

**RULES** describes what the function does. This is behavioral specification: given these inputs, what should happen? Rules are prose, not pseudocode. They describe outcomes, not steps.

```
RULES:
  - if neither ids nor tags provided, return all policies
  - if only ids provided, return policies matching those IDs
  - if only tags provided, return policies with at least one matching tag
  - if both provided, return union of matches, deduplicated
```

**DONE_WHEN** states how an agent knows the work is complete. These are observable criteria, not implementation details. An agent checks these conditions to determine whether to stop or continue.

```
DONE_WHEN:
  - returned list contains exactly the policies matching criteria
  - no duplicates in returned list
```

**EXAMPLES** provides concrete input-output pairs. These are mandatory. They serve as test cases, ground truth, and clarification of intent. If the rules are ambiguous, the examples disambiguate.

Examples must satisfy coverage criteria:
- Every conditional branch in RULES must have at least one example exercising it
- If a rule uses "or," "optionally," or other alternation, examples must show each path
- If the same set of examples could be produced by multiple conflicting interpretations of the rules, the specification is ambiguous

```
EXAMPLES:
  ([p1, p2, p3], none, none) → [p1, p2, p3]          # neither ids nor tags
  ([p1, p2, p3], [p1.id], none) → [p1]               # only ids
  ([p1, p2, p3], none, [python]) → matches with tag  # only tags
  ([p1, p2, p3], [p1.id], [python]) → union          # both provided
```

An example may optionally declare one of four observable kinds before its content:

- **value**: a concrete input produces an exact or structurally described value
- **error**: an input produces an observable failure response
- **outcome**: a setup or action produces observable state, files, artifacts, or other effects
- **property**: a behavioral property holds over a stated class of inputs or repeated observations

```
EXAMPLES:
  - [E1] value: (2, 3) → 5
  - [E2] error: ("x", 3) → fail with "input must be numeric"
  - [E3] outcome: build valid project → package imports and declared tests pass
  - [E4] property: any finite numeric a and b → add(a, b) equals add(b, a)
```

Kinds are optional authoring metadata. An unannotated example retains the v0.5 meaning. Every
example must still state an input, setup, or condition and an observable expected result; a kind
does not make a vague example valid.

**Stable item identifiers** may prefix list items in contract landmarks and examples. An
identifier uses ASCII letters, digits, `.`, `_`, and `-`, starts with a letter, and is enclosed in
square brackets. Identifiers are unique across the document. They do not change the meaning or
priority of an item.

```
RULES:
  - [R1] if neither ids nor tags are provided, return all policies

DONE_WHEN:
  - [D1] the returned list contains exactly the matching policies
```

Identifiers are optional unless another declaration references them. Prefixes such as `R`, `D`,
`E`, `X`, `P`, and `V` are conventions for readability, not separate namespaces or semantics.

**COVERS** declares traceability from identified examples to identified contract items. It is
optional and appears within a FUNCTION block.

```
COVERS:
  - E1 → R1, D1
  - E2 → R2, X1
```

Each row has exactly one source example and one or more targets. The source must identify an item
in that function's EXAMPLES block. A target must identify a contract item in the same function or
an item in a document-level CONSTRAINT block. A COVERS row cannot refer to another function's
local items.

COVERS records the author's claim that an example supplies evidence for a requirement. A linter
can deterministically verify identifier uniqueness, reference integrity, and whether identified
items have declared links. It cannot prove that an example actually exercises the target's
meaning. Reports must therefore distinguish **declared coverage** from proven semantic coverage.

**ERRORS** specifies what to do when things go wrong. It maps conditions to responses. This landmark is required. At minimum, it must specify default failure behavior.

A valid minimal ERRORS block:

```
ERRORS:
  - any unhandled condition → fail with descriptive message
```

A more complete ERRORS block:

```
ERRORS:
  - policy ID not found → fail with "unknown policy ID: {id}"
  - invalid YAML syntax → fail with "parse error: {details}"
  - any unhandled condition → fail with descriptive message
```

The requirement ensures agents never silently swallow failures during long-running autonomous execution.

**READS** declares what shared memory this function consumes. When agents coordinate through shared state, this landmark makes dependencies explicit.

```
READS:
  - SharedMemory.artifacts["registry_path"]
  - SharedMemory.status["validation_complete"]
```

**WRITES** declares what shared memory this function produces. Together with READS, this allows agents to understand data flow without central orchestration.

```
WRITES:
  - SharedMemory.artifacts["compiled_agents"]
  - SharedMemory.status["compilation"] = success | failure
```

**TRIGGERS** states conditions under which an agent should pick up this work. In swarm architectures where agents poll for available work, triggers help them decide what to do next.

```
TRIGGERS:
  - SharedMemory.artifacts["registry_path"] exists
  - SharedMemory.status["compilation"] != success
```

**NOT_ALLOWED** establishes boundaries. It states what the function must not do, even if it might seem reasonable. Use this sparingly; over-constraining defeats the purpose of implementation opacity.

```
NOT_ALLOWED:
  - modify source files
  - skip invalid entries silently
  - generate partial output on error
```

**HANDOFF** describes what passes to the next stage. On success, what does the receiving agent get? On failure, what information helps with recovery or escalation?

```
HANDOFF:
  - on success: CompiledArtifacts ready for write_artifacts
  - on failure: error message with file and line number
```

**UNCERTAIN** declares conditions under which an agent should signal low confidence rather than proceeding silently. This provides a structured way to handle ambiguity in long-running autonomous workflows.

```
UNCERTAIN:
  - if input format doesn't match any documented pattern → log warning and attempt best-effort parse
  - if multiple valid interpretations exist → pause and request clarification
  - if output would affect more than 100 files → require confirmation before proceeding
```

When UNCERTAIN is absent, agents proceed with best judgment and do not pause. When present, it defines explicit thresholds for caution.

UNCERTAIN does not violate the completeness pillar. The specification remains complete—it simply acknowledges that real-world inputs may fall outside documented cases and provides guidance for those situations.

**DETERMINISM** declares the expected consistency of function outputs. This landmark reduces implementation variance by making explicit whether repeated calls with identical inputs should produce identical outputs.

```
DETERMINISM:
  level: strict
  seed: from input hash
```

DETERMINISM contains:
- **level**: One of `strict` (identical outputs required), `structural` (same shape, values may vary), or `semantic` (equivalent meaning, representation may vary). Default when absent is `semantic`.
- **seed**: How to seed any random elements. Options include `from input hash` (deterministic based on inputs), `from timestamp` (reproducible within time window), or `none` (explicitly non-deterministic).

```
DETERMINISM:
  level: structural
  vary: ordering of equivalent items, whitespace formatting
  stable: all data values, field presence, error messages
```

The `vary` and `stable` fields provide fine-grained control:
- **vary**: Aspects of output that may differ between calls
- **stable**: Aspects that must remain consistent

When DETERMINISM is absent, agents have maximum implementation freedom. When present, it constrains the acceptable variance in implementations.

DETERMINISM interacts with EVAL thresholds. A function marked `level: strict` with `pass^k` testing ensures k identical runs produce identical results. A function marked `level: semantic` with `pass@k` testing allows variance as long as at least one run achieves the desired outcome.

---

## Required and Optional

Of the eighteen landmarks, five are always required for a valid specification. One additional landmark is conditionally required.

**FUNCTION** is required because without it there is no work to describe.

**RULES** is required because without it there is no behavior.

**DONE_WHEN** is required because without it agents cannot know when to stop.

**EXAMPLES** is required because without them there is no ground truth.

**ERRORS** is required because without it agents may fail silently during autonomous execution.

**EVAL** is conditionally required: when BASELINE is present, EVAL must also be present. Without EVAL, BASELINE's preserve/evolve distinction would have no measurement criteria, violating the completeness pillar.

Everything else is optional. A minimal valid spec consists of a function with rules, completion criteria, examples, and error handling. A minimal valid evolution spec adds BASELINE and EVAL. SIMPLEX declares language semantics when version-aware tooling is needed. COVERS adds auditable traceability when stable evidence links are useful. The optional landmarks add precision when needed, but their absence does not invalidate a spec.

**Variance control landmarks.** Three landmarks specifically target implementation variance:
- **DATA** (as output schema): When a function's return type references a DATA block, outputs must conform exactly
- **CONSTRAINT**: Behavioral anchors that narrow valid implementations
- **DETERMINISM**: Explicit control over output consistency requirements

These are optional but recommended when reducing implementation variance is important.

DATA is optional to define. But when a function's return type references a DATA block, conformance is required—the choice to use DATA is optional, the obligation to conform is not.

---

## Validation Criteria

A specification is valid if it passes structural and semantic validation.

### Structural Validation

- At least one FUNCTION block exists
- Every FUNCTION contains RULES, DONE_WHEN, EXAMPLES, and ERRORS
- DATA types referenced in FUNCTION signatures are defined or obvious from context
- CONSTRAINT blocks state verifiable invariants
- If BASELINE is present, it must contain reference, preserve, and evolve
- If BASELINE is present, EVAL must also be present
- If EVAL is present with BASELINE, it must contain preserve and evolve thresholds
- EVAL.grading must be one of: code, model, outcome
- If SIMPLEX is present, it occurs once and declares a supported `major.minor` version
- Stable item identifiers are unique across the document
- Every COVERS source resolves to an identified example in the same function
- Every COVERS target resolves to an identified local contract item or document-level constraint

### Semantic Validation

Semantic validation ensures the specification is unambiguous.

**Example coverage.** Every conditional path in RULES must be exercised by at least one example.

- Count the branches: "if X" is one branch; "if X or Y" is two branches; "if X, else Y" is two branches
- Each branch needs at least one example demonstrating it
- Missing coverage is a validation error

**Interpretation uniqueness.** The examples must not be satisfiable by conflicting interpretations.

- If an agent could imagine two different implementations that both pass all examples but would behave differently on some unstated input, the specification is ambiguous
- This is a heuristic, not a formal proof—agents should flag suspected ambiguity

**Observable completion.** DONE_WHEN criteria must be checkable from outside the function.

- "Internal state is consistent" is not observable—invalid
- "Output contains no duplicates" is observable—valid
- "All items processed" is observable only if processing produces visible evidence—clarify

**Behavioral rules.** RULES must describe outcomes, not procedures.

- "Loop through items and check each" is procedural—invalid
- "All items matching criteria are included in output" is behavioral—valid

**Evolution coverage.** When BASELINE is present, every item in preserve and evolve should have at least one corresponding example.

- Preserved behaviors need examples that verify regression protection
- Evolved capabilities need examples that demonstrate the new behavior
- Examples should be classifiable as testing preserved vs. evolved behavior based on what they exercise

**Declared traceability.** When COVERS is present, every mapping must resolve and tooling should
report identified requirements or examples that have no declared link.

- A complete mapping is evidence that the author connected examples to contract items
- It is not proof that the examples semantically exercise those items
- Semantic review remains necessary to detect false, weak, or misleading mappings
- The catch-all `any unhandled` error is not an automatic coverage obligation because it does not
  identify a concrete failure scenario; specific error conditions remain traceable items

---

## Shared Memory

When agents coordinate through shared state—a knowledge graph, a key-value store, a file system—the READS, WRITES, and TRIGGERS landmarks describe interaction patterns.

However, Simplex does not define what shared memory is or how it works. It only provides landmarks for describing contracts against it. The implementation of shared memory is an agent concern.

A specification might say:

```
READS:
  - SharedMemory.knowledge_graph (policy relationships)

WRITES:
  - SharedMemory.artifacts["compiled_output"]
```

Whether SharedMemory is a graph database, a Redis instance, or a directory of JSON files is not the spec's concern. The contract is that something called SharedMemory exists, supports these operations, and agents can rely on it.

---

## Linter Specification

The following specification describes the deterministic checks implemented by the bundled Go
linter. It enforces a limited, mechanically checkable subset of the broader validation criteria.
The linter does not execute examples, prove branch coverage or COVERS claims, check interpretation
uniqueness or observability, validate output schemas, or perform LLM-based semantic review. Its
`valid` field means that the implemented error checks passed.

```
DATA: LintResult
  valid: boolean
  errors: list of LintError
  warnings: list of LintWarning

DATA: LintError
  location: string, which landmark or line
  code: string, error identifier
  message: string, human-readable explanation

DATA: LintWarning
  location: string
  code: string
  message: string

FUNCTION: lint_spec(spec_text) → LintResult

  RULES:
    - parse spec_text to identify all landmarks and their content
    - check structural validity: required landmarks present
    - check declared language version when present
    - check stable identifiers and COVERS reference integrity
    - check complexity limits and compare heuristic branch and example counts
    - check BASELINE, EVAL, and DETERMINISM fields supported by this linter
    - collect all errors and warnings
    - spec is valid only if zero errors

  DONE_WHEN:
    - all landmarks examined
    - all checks performed
    - LintResult populated with findings

  EXAMPLES:
    (minimal valid spec) → {valid: true, errors: [], warnings: []}
    (missing ERRORS landmark) → {valid: false, errors: [{code: "E005", ...}], warnings: []}
    (RULES block over limit) → {valid: false, errors: [{code: "E010", ...}], warnings: []}
    (fewer examples than heuristic branches) → {valid: false, errors: [{code: "E012", ...}], warnings: []}
    (COVERS references unknown ID) → {valid: false, errors: [{code: "E103", ...}], warnings: []}

  ERRORS:
    - lint findings are returned in LintResult rather than thrown
    - CLI input or option failure → terminate the invocation with a descriptive message

FUNCTION: check_structure(spec) → list of LintError

  RULES:
    - no FUNCTION block → error E001
    - missing RULES, DONE_WHEN, EXAMPLES, or ERRORS → error E002, E003, E004, or E005
    - required landmark present without content → error E006
    - repeated function-level landmark → error E007
    - malformed FUNCTION signature → error E008
    - repeated FUNCTION name in one document → error E009
    - return type that may reference an undefined DATA block → warning W006

  DONE_WHEN:
    - all functions and required landmarks examined
    - structural issues collected

  EXAMPLES:
    (one well-formed function with all required landmarks) → []
    (function with an empty ERRORS block) → [E006]
    (two functions with the same name) → [E009]

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_complexity(spec) → list of LintError

  RULES:
    - RULES block exceeds 15 items → error E010 "RULES too complex: {count} items, max 15"
    - FUNCTION has more than 6 inputs → error E011 "too many inputs: {count}, max 6"
    - EXAMPLES fewer than heuristic branch count in RULES → error E012
    - single RULES item exceeds 200 characters → warning W010 "rule may be too complex"
    - spec contains more than 10 FUNCTION blocks → warning W011 "consider splitting into multiple specs"

  DONE_WHEN:
    - all complexity thresholds checked
    - errors collected

  EXAMPLES:
    (spec with 5 RULES items, 3 inputs, 4 examples for 4 branches) → []
    (spec with 20 RULES items) → [E010]
    (spec with 8 inputs) → [E011]
    (spec with 2 examples for 4 heuristic branches) → [E012]

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_version(spec) → declared version or unspecified

  RULES:
    - SIMPLEX is optional for backward compatibility
    - when present, SIMPLEX must contain one major.minor version
    - malformed or extra declaration content → error E090
    - unsupported declared version → error E091
    - repeated SIMPLEX declaration → error E092
    - COVERS with declared version 0.5 → error E093
    - COVERS without a declaration → warning W090
    - supported declared versions are 0.5 and 0.6
    - report the declared version separately from the newest supported version

  DONE_WHEN:
    - all SIMPLEX declarations examined
    - version-dependent COVERS use checked

  EXAMPLES:
    (no declaration and no COVERS) → unspecified with no version issue
    (SIMPLEX 0.6 with COVERS) → version 0.6 with no version issue
    (SIMPLEX 0.5 with COVERS) → E093

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_baseline(baseline) → list of LintError

  RULES:
    - if BASELINE is present, it must contain reference field
    - if BASELINE is present, it must contain preserve field with at least one item
    - if BASELINE is present, it must contain evolve field with at least one item
    - missing reference → error E050 "BASELINE requires reference field"
    - missing preserve → error E051 "BASELINE requires preserve field"
    - missing evolve → error E052 "BASELINE requires evolve field"
    - empty preserve list → error E053 "BASELINE preserve must contain at least one item"
    - empty evolve list → error E054 "BASELINE evolve must contain at least one item"

  DONE_WHEN:
    - BASELINE structure validated
    - all required fields checked

  EXAMPLES:
    (baseline with reference, preserve, evolve) → []
    (baseline missing reference) → [E050]
    (baseline with empty preserve) → [E053]

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_eval(eval, baseline_present) → list of LintError

  RULES:
    - if BASELINE is present, EVAL must also be present
    - if BASELINE is present, EVAL must contain preserve threshold
    - if BASELINE is present, EVAL must contain evolve threshold
    - BASELINE present but EVAL absent → error E060 "EVAL required when BASELINE present"
    - preserve threshold missing when BASELINE present → error E061 "EVAL requires preserve threshold when BASELINE present"
    - evolve threshold missing when BASELINE present → error E062 "EVAL requires evolve threshold when BASELINE present"
    - preserve threshold must be pass^k notation → error E063 "preserve threshold must use pass^k notation"
    - evolve threshold must be pass@k notation → error E064 "evolve threshold must use pass@k notation"
    - grading must be code, model, or outcome → error E065 "grading must be code, model, or outcome"
    - k in pass^k and pass@k must be a positive integer; otherwise report E063 or E064

  DONE_WHEN:
    - EVAL presence checked against BASELINE
    - all threshold notations validated
    - grading type validated

  EXAMPLES:
    (eval with pass^3, pass@5, code; baseline present) → []
    (no eval; baseline present) → [E060]
    (eval with invalid threshold "pass3") → [E063 or E064]
    (eval with grading "fuzzy") → [E065]

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_determinism(determinism) → list of LintError

  RULES:
    - if DETERMINISM is present, level must be one of: strict, structural, semantic
    - invalid level → error E070 "DETERMINISM level must be strict, structural, or semantic"

  DONE_WHEN:
    - DETERMINISM structure validated
    - level checked

  EXAMPLES:
    (determinism with level: strict, seed: from input hash) → []
    (determinism with level: fuzzy) → [E070]

  ERRORS:
    - any unhandled condition → fail with descriptive message

FUNCTION: check_traceability(spec) → declared coverage report

  RULES:
    - collect stable item identifiers at the start of contract and example items; duplicates → error E100
    - parse each COVERS row as one example ID followed by one or more target IDs
    - source IDs must resolve to EXAMPLES in the same function
    - target IDs must resolve to contract items in that function or document-level CONSTRAINT items
    - malformed COVERS row → error E101
    - unknown or non-example source → error E102
    - unknown or out-of-scope target → error E103
    - target that resolves to another example → error E104
    - invalid stable identifier → error E105
    - identified expected target without a link → warning W100
    - identified example without a link → warning W101
    - unlabelled traceable items when COVERS is present → warning W102
    - report counts for identifiers, links, coverable items, covered items, and gaps
    - never describe declared links as proof of semantic coverage

  DONE_WHEN:
    - all identifiers and COVERS rows examined
    - broken references reported deterministically
    - declared coverage statistics populated

  EXAMPLES:
    - (E1 → R1 and both IDs resolve in one function) → one valid declared coverage link
    - (E1 → missing) → E103
    - (unknown → R1) → E102
    - (duplicate R1 identifiers) → E100
    - (COVERS present but R2 has no link) → W100 and incomplete declared traceability

  ERRORS:
    - any unhandled condition → fail with descriptive message

CONSTRAINT: linter_thresholds
  the specific numeric limits (15 rules, 6 inputs, 200 chars) are defaults
  implementations may allow configuration
  the principle is enforced simplicity, not specific numbers
```

---

## Meta-Specification

Simplex can describe itself. The following specification defines how agents should interpret Simplex documents.

```simplex
SIMPLEX: 0.6

DATA: Landmark
  name: string, all caps
  purpose: what it communicates
  required: yes | no | conditional

DATA: Spec
  functions: one or more FUNCTION blocks
  data: zero or more DATA blocks
  constraints: zero or more CONSTRAINT blocks

FUNCTION: parse_spec(text) → Spec

  RULES:
    - landmarks are all-caps words followed by colon
    - required: FUNCTION, RULES, DONE_WHEN, EXAMPLES, ERRORS
    - conditionally required: EVAL (when BASELINE present)
    - optional: SIMPLEX, DATA, CONSTRAINT, BASELINE, EVAL, COVERS, READS, WRITES, TRIGGERS, NOT_ALLOWED, HANDOFF, UNCERTAIN, DETERMINISM
    - content continues until next landmark or end
    - tolerate formatting inconsistency
    - extract meaning not syntax
    - ignore unrecognized landmarks

  DONE_WHEN:
    - all FUNCTION blocks identified with nested landmarks
    - all DATA and CONSTRAINT blocks identified
    - BASELINE and EVAL blocks identified when present

  ERRORS:
    - no FUNCTION found → "invalid spec: no functions"
    - any unhandled condition → fail with descriptive message

  EXAMPLES:
    (well-formed text) → Spec
    (sloppy formatting) → Spec if meaning clear
    (unknown landmarks) → Spec, unknowns ignored
    (missing ERRORS) → "invalid spec: ERRORS required"
    (BASELINE without EVAL) → "invalid spec: EVAL required when BASELINE present"

FUNCTION: validate_spec(spec) → valid | issues

  RULES:
    - FUNCTION requires RULES, DONE_WHEN, EXAMPLES, ERRORS
    - RULES must be behavioral rather than procedural, and DONE_WHEN must be externally observable
    - EXAMPLES must cover every conditional branch and must not permit conflicting interpretations
    - ERRORS must specify at least default failure behavior
    - referenced DATA types must be defined or obvious, and CONSTRAINT must state verifiable invariants
    - BASELINE requires reference, preserve, evolve, and a corresponding EVAL
    - EVAL with BASELINE requires preserve/evolve thresholds and grading of code, model, or outcome
    - preserve/evolve items in BASELINE should have corresponding examples
    - if DETERMINISM present, level must be valid (strict, structural, semantic)
    - if return type references DATA, examples must conform to that schema
    - if SIMPLEX present, it must declare a supported language version
    - stable item identifiers must be document-unique
    - COVERS references must resolve within their declared scope
    - declared coverage completeness is reported separately from semantic coverage

  DONE_WHEN:
    - structural checks complete
    - semantic checks complete
    - evolution checks complete (when BASELINE present)
    - variance control checks complete (when DETERMINISM or output schema present)
    - all issues collected

  ERRORS:
    - none; issues are returned, not thrown
    - any unhandled condition → fail with descriptive message

  EXAMPLES:
    (complete spec with full coverage) → valid
    (missing ERRORS landmark) → issues: ["E005: ERRORS required"]
    (uncovered branch) → issues: ["semantic review: branch X not covered"]
    (procedural RULES) → issues: ["semantic review: RULES should be behavioral"]
    (non-observable DONE_WHEN) → issues: ["semantic review: criterion not observable"]
    (BASELINE without EVAL) → issues: ["E060: EVAL required when BASELINE present"]
    (EVAL with invalid threshold) → issues: ["E063: preserve threshold must use pass^k notation"]
    (DETERMINISM with invalid level) → issues: ["E070: DETERMINISM level must be strict, structural, or semantic"]
    (example missing required field from output schema) → issues: ["schema review: required field missing"]
    (COVERS target does not resolve) → issues: ["E103: unknown COVERS target"]

CONSTRAINT: self_description
  this specification is parseable by parse_spec
  this specification is intended to satisfy validate_spec; semantic criteria require review
  this specification passes the implemented deterministic lint_spec checks with zero errors
```

The self-description constraint is a project invariant: future versions of Simplex should remain self-describing and pass the applicable linter checks. The canonical meta-specification above is the only live Simplex region in this Markdown document. In auto mode, `simplex-lint` ignores the other fenced illustrations, and CI checks `spec/simplex.md` for zero deterministic errors. That gate does not establish the semantic checks described by `validate_spec`; those still require review.

---

## Usage Guidance

When writing a Simplex specification, start with the function signature and examples. The examples force clarity about inputs and outputs before you describe behavior. Many specification errors become obvious when you try to write concrete examples.

Next, write the rules. Describe behavior, not implementation. If you catch yourself writing "loop through" or "create a variable," step back. Describe what should be true of the output, not how to compute it.

Then write the completion criteria. These should be observable from outside the function. "Internal data structure is consistent" is not observable. "Output contains no duplicates" is observable.

Write the error handling. At minimum, specify that unhandled conditions fail with descriptive messages. For functions with known failure modes, map specific conditions to specific responses.

Add optional landmarks only as needed. A simple function may need nothing beyond the required five. A function that interacts with shared memory or has complex coordination needs benefits from READS, WRITES, TRIGGERS. A function operating in uncertain environments benefits from UNCERTAIN.

Add stable identifiers and COVERS when reviewers or tools need to audit how examples relate to
requirements. Treat the resulting map as a traceability assertion. Review whether each mapped
example really exercises its targets; a mechanically complete map can still be semantically weak.

If a specification becomes unwieldy, decompose it. Multiple simple specs are better than one complex spec. If the linter flags complexity errors, that is a signal to break the work into smaller pieces.

Run the linter before considering a specification complete. A passing result means the document satisfies the checks implemented by that linter version. Semantic validity remains a broader requirement and still requires review beyond the current deterministic checks.

---

## Version History

**v0.6** — Added optional SIMPLEX language-version declarations, document-wide stable item
identifiers, the COVERS landmark for example-to-contract traceability, and optional value, error,
outcome, and property example kinds. Declared coverage is explicitly distinguished from semantic
coverage proof. A v0.5 document does not need identifiers or COVERS to remain valid. Added deterministic checks for
version declarations, identifier uniqueness, COVERS reference integrity, and traceability gaps.

**v0.5** — Added variance reduction features. Enhanced CONSTRAINT as behavioral anchors with examples of state invariants, output guarantees, and boundary conditions. Added DETERMINISM landmark for explicit control over output consistency (strict/structural/semantic levels, seed specification, vary/stable fields). Strengthened DATA as required output schemas—when a function return type references a DATA block, outputs must conform exactly. Added `not allowed` field annotation and conditional field presence. Added deterministic DETERMINISM-level checks; output-schema validation remains specified but is not implemented. Updated meta-specification and validation for new landmarks.

*v0.5 variance reduction features address the gap between specification intent and implementation variance. When agents have implementation freedom, outputs can vary in structure, ordering, and detail even when semantically equivalent. These landmarks provide spec authors with tools to constrain variance where consistency matters.*

**v0.4** — Added BASELINE and EVAL landmarks for evolutionary specifications. BASELINE declares what to preserve and evolve relative to a reference state. EVAL declares grading approach and consistency thresholds using pass^k (all trials must pass) and pass@k (at least one trial must pass) notation. These landmarks address agent failure modes in long-horizon software evolution scenarios. EVAL is required when BASELINE is present to ensure measurement criteria are explicit. Added deterministic BASELINE/EVAL structure checks; preservation/evolution example coverage remains specified but is not implemented. Updated meta-specification for conditional landmark requirements.

*v0.4 landmark additions informed by SWE-EVO research [1].*

**v0.3** — Made ERRORS required. Added UNCERTAIN landmark for confidence signaling. Added Validation Criteria section with semantic ambiguity detection. Added Linter Specification and updated the meta-specification for new requirements.

**v0.2** — Established pillars, landmarks, interpretation model, and meta-specification.

**v0.1** — Initial exploration. Identified need for specification targeting autonomous agents.

## References

[1] Y. Liu et al., "SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios," arXiv:2512.18470, December 2025. https://arxiv.org/abs/2512.18470
