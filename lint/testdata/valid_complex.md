# Valid Complex Spec

A more complex but still valid Simplex specification with multiple functions
and optional landmarks.

DATA: PolicyRule
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
  - return policies not in the input list

FUNCTION: validate_policies(policies) → valid | issues

RULES:
  - check each policy against all CONSTRAINT blocks
  - collect all validation issues
  - return valid if no issues, otherwise return list of issues

DONE_WHEN:
  - all policies checked against all constraints
  - all issues collected and returned

EXAMPLES:
  ([valid_p1, valid_p2]) → valid
  ([p1_with_duplicate_id, p2]) → issues: ["duplicate ID: XXX-001"]
  ([]) → valid

ERRORS:
  - any unhandled condition → fail with descriptive message

HANDOFF:
  - on success (valid): policies ready for use
  - on failure (issues): list of issues for human review
