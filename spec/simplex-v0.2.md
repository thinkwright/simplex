# Simplex

A specification language for autonomous agents.

Version 0.2

---

## Purpose

Simplex is a language for describing work that autonomous agents will perform. It captures what needs to be done and how to know when it's done, without prescribing how to do it. The language is designed to be interpreted by large language models directly, without formal parsing.

The motivation is practical. When agents work autonomously for extended periods—hours or days—they need instructions that are complete enough to act on without clarification, yet flexible enough to allow implementation choices. Simplex occupies this middle ground between natural language (too ambiguous) and programming languages (too prescriptive).

---

## Pillars

Six principles guide the language design.

**Enforced simplicity.** The language refuses to support constructs that would allow specifications to become unwieldy. If something cannot be expressed simply, it must be decomposed into smaller pieces first. This is a feature, not a limitation. Complexity that cannot be decomposed is complexity that is not yet understood.

**Syntactic tolerance, semantic precision.** The language forgives formatting inconsistencies, typos, and notational variations. Agents interpret what you meant, not what you typed. However, the meaning itself must be unambiguous. If an agent would have to guess your intent, the specification is invalid. Sloppy notation is acceptable; vague meaning is not.

**Specification, not implementation.** A Simplex spec describes what and constraints, never how. The moment you find yourself specifying algorithms, data structures, or technology choices, you have crossed into implementation. Pull back. Describe the behavior you need and the conditions that must hold. Let agents determine the approach.

**Testability.** Every function requires examples. These are not illustrations; they are contracts. The examples define what correct output looks like for given inputs. An agent's work is not complete until its output is consistent with the examples.

**Completeness.** A valid specification must be sufficient to generate working code without further clarification. This is what distinguishes Simplex from a prompting language. There is no back-and-forth, no "what did you mean by X?" The spec must stand alone.

**Implementation opacity.** Specifications describe contracts and constraints. Implementation choices belong to agents. If a spec needs a persistent data store, it says so. Whether agents implement that as a graph database, a file system, or something else entirely is their concern. The spec neither knows nor cares.

---

## Interpretation Model

Simplex has no formal grammar. There is no parser, no AST, no compilation step. Agents read specifications as semi-structured text and extract meaning directly.

This is intentional. A formal grammar would contradict the principle of syntactic tolerance. It would also add complexity and create failure modes. Since the language exists for LLM interpretation, it should be native to how LLMs work.

Instead of grammar rules, Simplex uses landmarks. Landmarks are structural markers that agents recognize and orient around. They are all-caps words followed by a colon. Content under a landmark continues until the next landmark or the end of the document.

Agents scan for landmarks, extract the content associated with each, and build understanding from there. Unrecognized landmarks are ignored rather than rejected, which provides forward compatibility as the language evolves.

---

## Landmarks

Simplex defines twelve landmarks. Three describe structure. Nine describe functions.

### Structural Landmarks

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

**CONSTRAINT** states an invariant that must hold. Unlike function-specific rules, constraints apply broadly. They describe conditions that should never be violated, regardless of which function is executing.

```
CONSTRAINT: policy_ids_must_exist
  any policy ID referenced anywhere must exist in the registry
```

**FUNCTION** introduces a unit of work. It names an operation, lists its inputs, and declares its return type. The function block contains nested landmarks that specify behavior, completion criteria, and test cases.

```
FUNCTION: filter_policies(policies, ids, tags) → filtered list
```

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

```
EXAMPLES:
  ([p1, p2, p3], [p1.id], none) → [p1]
  ([p1, p2, p3], none, [python]) → all with "python" in tags
  ([p1, p2, p3], none, none) → [p1, p2, p3]
```

**ERRORS** specifies what to do when things go wrong. It maps conditions to responses. Without this landmark, agents use their judgment on error handling.

```
ERRORS:
  - policy ID not found → fail with "unknown policy ID: {id}"
  - invalid YAML syntax → fail with "parse error: {details}"
```

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

---

## Required and Optional

Of the twelve landmarks, four are required for a valid specification.

FUNCTION is required because without it there is no work to describe.

RULES is required because without it there is no behavior.

DONE_WHEN is required because without it agents cannot know when to stop.

EXAMPLES is required because without them there is no ground truth.

Everything else is optional. A minimal valid spec consists of a function with rules, completion criteria, and examples. The optional landmarks add precision when needed, but their absence does not invalidate a spec.

---

## Composition

Simplex does not have a composition construct. There is no way to formally specify that one function calls another, or that functions must execute in a particular order.

This is intentional. Composition is emergent. Agents read the full specification and determine how to decompose and sequence work. If a spec author wants to suggest decomposition, they can write multiple FUNCTION blocks and let agents infer relationships. But the language does not enforce it.

The reasoning is practical. Prescribed composition is fragile. It assumes the spec author knows the best way to structure the work. Often they do not. Agents operating over hours may discover better decompositions than the author imagined. The language should not prevent this.

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

## Meta-Specification

Simplex can describe itself. The following specification defines how agents should interpret Simplex documents.

```
DATA: Landmark
  name: string, all caps
  purpose: what it communicates
  required: yes | no

DATA: Spec
  functions: one or more FUNCTION blocks
  data: zero or more DATA blocks
  constraints: zero or more CONSTRAINT blocks

FUNCTION: parse_spec(text) → Spec

  RULES:
    - landmarks are all-caps words followed by colon
    - required: FUNCTION, RULES, DONE_WHEN, EXAMPLES
    - optional: DATA, CONSTRAINT, ERRORS, READS, WRITES, TRIGGERS, NOT_ALLOWED, HANDOFF
    - content continues until next landmark or end
    - tolerate formatting inconsistency
    - extract meaning not syntax
    - ignore unrecognized landmarks

  DONE_WHEN:
    - all FUNCTION blocks identified with nested landmarks
    - all DATA and CONSTRAINT blocks identified

  ERRORS:
    - no FUNCTION found → "invalid spec: no functions"

  EXAMPLES:
    (well-formed text) → Spec
    (sloppy formatting) → Spec if meaning clear
    (unknown landmarks) → Spec, unknowns ignored

FUNCTION: validate_spec(spec) → valid | issues

  RULES:
    - FUNCTION requires RULES, DONE_WHEN, EXAMPLES
    - RULES must be behavioral
    - DONE_WHEN must be observable
    - EXAMPLES must show input → output
    - DATA referenced must exist
    - CONSTRAINT must be verifiable

  DONE_WHEN:
    - all checked
    - issues collected

  ERRORS:
    - none; issues returned

  EXAMPLES:
    (complete spec) → valid
    (missing required landmark) → issues list

CONSTRAINT: self_description
  this specification is parseable by parse_spec
  this specification passes validate_spec
```

The self-description constraint is meaningful. Any future version of Simplex must remain self-describing. This provides a check on language evolution: changes that break self-description are changes that have gone too far.

---

## Usage Guidance

When writing a Simplex specification, start with the function signature and examples. The examples force clarity about inputs and outputs before you describe behavior. Many specification errors become obvious when you try to write concrete examples.

Next, write the rules. Describe behavior, not implementation. If you catch yourself writing "loop through" or "create a variable," step back. Describe what should be true of the output, not how to compute it.

Then write the completion criteria. These should be observable from outside the function. "Internal data structure is consistent" is not observable. "Output contains no duplicates" is observable.

Add optional landmarks only as needed. A simple function may need nothing beyond the required four. A function that interacts with shared memory or has complex failure modes benefits from additional landmarks.

If a specification becomes unwieldy, decompose it. Multiple simple specs are better than one complex spec. The enforced simplicity pillar exists for this reason: if you cannot express something simply, you do not yet understand it well enough to specify it.

---

## Version History

**v0.2** — Current version. Established pillars, landmarks, interpretation model, and meta-specification.

**v0.1** — Initial exploration. Identified need for specification language targeting autonomous agents.
