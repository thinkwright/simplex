package checks

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/thinkwright/simplex/lint/internal/parser"
	"github.com/thinkwright/simplex/lint/internal/result"
)

func checkTraceability(t *testing.T, source string) *result.LintResult {
	t.Helper()
	parsed := parser.NewParser().Parse(source)
	r := result.NewLintResult("test.simplex")
	NewTraceabilityChecker().Check(parsed, r)
	return r
}

func TestTraceabilityCheckerIgnoresUnlabelledLegacyDocument(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: add(a, b) → number
RULES:
  - return the sum
EXAMPLES:
  (2, 3) → 5`)
	assert.Nil(t, r.Stats.Traceability)
	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
}

func TestTraceabilityCheckerReportsCompleteDeclaredCoverage(t *testing.T) {
	r := checkTraceability(t, `CONSTRAINT: safety
  - [C1] output is safe

FUNCTION: add(a, b) → number
RULES:
  - [R1] return the sum
DONE_WHEN:
  - [D1] result equals a + b
EXAMPLES:
  - [E1] value: (2, 3) → 5
  - [E2] property: finite a and b → add(a,b) equals add(b,a)
ERRORS:
  - [X0] any unhandled condition → fail descriptively
COVERS:
  - [E1] -> [R1], [D1], [C1]
  - E2 → R1, D1`)

	assert.True(t, r.Valid)
	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
	require.NotNil(t, r.Stats.Traceability)
	trace := r.Stats.Traceability
	assert.True(t, trace.Declared)
	assert.True(t, trace.Complete)
	assert.Equal(t, 6, trace.Identifiers)
	assert.Equal(t, 2, trace.ExampleIdentifiers)
	assert.Equal(t, 5, trace.Links)
	assert.Equal(t, 2, trace.CoverableItems)
	assert.Equal(t, 2, trace.CoveredItems)
	assert.Equal(t, map[string]int{"value": 1, "property": 1}, trace.ExampleKinds)
}

func TestTraceabilityCheckerCollectsAllExampleKinds(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: f() → result
EXAMPLES:
  - [E1] value: input → output
  - [E2] error: bad input → failure
  - [E3] outcome: setup → file exists
  - [E4] property: all inputs → invariant
  - [E5] input → result`)

	require.NotNil(t, r.Stats.Traceability)
	assert.Equal(t, map[string]int{
		"value": 1, "error": 1, "outcome": 1, "property": 1, "unclassified": 1,
	}, r.Stats.Traceability.ExampleKinds)
	assert.False(t, r.Stats.Traceability.Declared)
}

func TestTraceabilityCheckerRejectsDuplicateAndInvalidIdentifiers(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: f() → result
RULES:
  - [R1] first
  - [R1] second
  - [1bad] invalid
EXAMPLES:
  - [E1] input → output`)

	assert.False(t, r.Valid)
	assert.Contains(t, issueCodes(r.Errors), "E100")
	assert.Contains(t, issueCodes(r.Errors), "E105")
	require.NotNil(t, r.Stats.Traceability)
	assert.False(t, r.Stats.Traceability.Complete)
}

func TestTraceabilityCheckerRejectsBrokenReferencesAndScope(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: first() → result
RULES:
  - [R1] first rule
EXAMPLES:
  - [E1] input → output
COVERS:
  - missing → R1
  - R1 → R1
  - E1 → missing
  - E1 → E1
  - malformed row

FUNCTION: second() → result
RULES:
  - [R2] second rule
EXAMPLES:
  - [E2] input → output
COVERS:
  - E2 → R1`)

	codes := issueCodes(r.Errors)
	assert.Contains(t, codes, "E101")
	assert.Contains(t, codes, "E102")
	assert.Contains(t, codes, "E103")
	assert.Contains(t, codes, "E104")
	require.NotNil(t, r.Stats.Traceability)
	assert.False(t, r.Stats.Traceability.Complete)
}

func TestTraceabilityCheckerRejectsMalformedCoverageIdentifiersAndEmptyBlock(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: first() → result
RULES:
  - [R1] rule
EXAMPLES:
  - [E1] input → output
COVERS:
  - 1bad → R1
  - E1 →
  - E1 → bad target

FUNCTION: second() → result
RULES:
  - [R2] rule
EXAMPLES:
  - [E2] input → output
COVERS:
`)

	for _, issue := range r.Errors {
		assert.Equal(t, "E101", issue.Code)
	}
	assert.GreaterOrEqual(t, len(r.Errors), 4)
}

func TestTraceabilityCheckerWarnsAboutCoverageGapsAndUnlabelledItems(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: f() → result
RULES:
  - [R1] linked rule
  - [R2] unlinked rule
  - unlabelled rule
DONE_WHEN:
  - unlabelled completion
EXAMPLES:
  - [E1] input → output
  - [E2] other → result
  - unlabelled → result
ERRORS:
  - [X1] invalid input → fail
  - any unhandled condition → fail
COVERS:
  - E1 → R1`)

	codes := issueCodes(r.Warnings)
	assert.Contains(t, codes, "W100")
	assert.Contains(t, codes, "W101")
	assert.Contains(t, codes, "W102")
	trace := r.Stats.Traceability
	require.NotNil(t, trace)
	assert.False(t, trace.Complete)
	assert.Equal(t, 3, trace.UnlabelledItems)
	assert.Equal(t, 2, trace.UnlinkedExamples)
	assert.Equal(t, 5, trace.CoverableItems)
	assert.Equal(t, 1, trace.CoveredItems)
	assert.Equal(t, 4, trace.UncoveredItems)
}

func TestTraceabilityCheckerCoversBaselineDeterminismAndOptionalContracts(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: evolve() → result
BASELINE:
  reference: current
  preserve:
    - [P1] old behavior remains
  evolve:
    - [V1] new behavior exists
RULES:
  - [R1] return result
DONE_WHEN:
  - [D1] result observable
EXAMPLES:
  - [E1] outcome: baseline → preserved and evolved result
ERRORS:
  - [X0] any unhandled condition → fail
NOT_ALLOWED:
  - [N1] do not break API
READS:
  - [A1] repository
WRITES:
  - [A2] updated repository
TRIGGERS:
  - [A3] work requested
HANDOFF:
  - [A4] result to caller
UNCERTAIN:
  - [A5] ambiguous input → request clarification
DETERMINISM:
  level: structural
  stable:
    - [S1] result shape
  vary:
    - [Y1] equivalent formatting
COVERS:
  - E1 → P1, V1, R1, D1, N1, A1, A2, A3, A4, A5, S1, Y1`)

	assert.True(t, r.Valid)
	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
	require.NotNil(t, r.Stats.Traceability)
	assert.True(t, r.Stats.Traceability.Complete)
	assert.Equal(t, 12, r.Stats.Traceability.CoverableItems)
	assert.Equal(t, 12, r.Stats.Traceability.CoveredItems)
}

func TestTraceabilityCheckerDeduplicatesRepeatedLinks(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: f() → result
RULES:
  - [R1] rule
EXAMPLES:
  - [E1] input → output
COVERS:
  - E1 → R1, R1
  - E1 → R1`)

	require.NotNil(t, r.Stats.Traceability)
	assert.Equal(t, 1, r.Stats.Traceability.Links)
	assert.True(t, r.Stats.Traceability.Complete)
}

func TestTraceabilityCheckerScopesCompletenessToFunctionsWithCovers(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: legacy() → result
RULES:
  - [legacy.R1] legacy rule
EXAMPLES:
  - [legacy.E1] input → output

FUNCTION: traced() → result
RULES:
  - [traced.R1] traced rule
EXAMPLES:
  - [traced.E1] value: input → output
COVERS:
  - traced.E1 → traced.R1`)

	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
	require.NotNil(t, r.Stats.Traceability)
	assert.True(t, r.Stats.Traceability.Complete)
	assert.Equal(t, 1, r.Stats.Traceability.CoverableItems)
	assert.Equal(t, 1, r.Stats.Traceability.CoveredItems)
}

func TestTraceabilityCheckerReportsUnlabelledSectionItems(t *testing.T) {
	r := checkTraceability(t, `FUNCTION: f() → result
RULES:
  - [R1] return result
EXAMPLES:
  - [E1] value: input → result
DETERMINISM:
  level: structural
  stable:
    - result shape
  vary:
    - [V1] equivalent formatting
COVERS:
  - E1 → R1, V1`)

	assert.Contains(t, issueCodes(r.Warnings), "W102")
	require.NotNil(t, r.Stats.Traceability)
	assert.Equal(t, 1, r.Stats.Traceability.UnlabelledItems)
	assert.Equal(t, 1, r.Stats.Traceability.UncoveredItems)
	assert.False(t, r.Stats.Traceability.Complete)
}

func TestTraceabilitySectionAndItemParsingEdgeCases(t *testing.T) {
	r := result.NewLintResult("test")
	items, totals := collectSectionItems(`
# comment
not a field
unknown:
  - [U1] ignored because the field is not traceable
stable:
  -
  - unlabelled
  - [1bad] invalid
  - [S1] stable value
`, map[string]string{"stable": "DETERMINISM.stable"}, "FUNCTION f", 0, r)

	require.Len(t, items, 1)
	assert.Equal(t, "S1", items[0].id)
	assert.Equal(t, 3, totals["DETERMINISM.stable"])
	assert.Contains(t, issueCodes(r.Errors), "E105")

	_, ok := itemText("", false)
	assert.False(t, ok)
	_, ok = itemText("# comment", false)
	assert.False(t, ok)
	_, ok = itemText("- prose without an outcome", true)
	assert.False(t, ok)
	_, ok = itemText("-", false)
	assert.False(t, ok)

	rows, malformed := parseCoverageRows(
		parser.FunctionBlock{Name: "f"},
		parser.Landmark{Content: "\n# comment\nE1 → R1"},
		result.NewLintResult("test"),
	)
	assert.False(t, malformed)
	require.Len(t, rows, 1)
	assert.Equal(t, "E1", rows[0].source)
}

func TestTraceabilityHelpers(t *testing.T) {
	left, right, ok := splitCoverageArrow("E1 -> R1")
	assert.True(t, ok)
	assert.Equal(t, "E1 ", left)
	assert.Equal(t, " R1", right)
	_, _, ok = splitCoverageArrow("E1 R1")
	assert.False(t, ok)
	assert.Equal(t, "E1", trimBrackets("[ E1 ]"))
	assert.Equal(t, "E1", trimBrackets("E1"))
	assert.Equal(t, "error", parseExampleKind("error: bad → fail"))
	assert.Equal(t, "unclassified", parseExampleKind("custom: input → output"))
	assert.Equal(t, "unclassified", parseExampleKind("input → output"))
	assert.True(t, isDefaultFailure("Any Unhandled condition"))
	assert.False(t, isDefaultFailure("known failure"))

	roles := sortedTraceRoles(map[string]int{"ZZZ": 1, parser.LandmarkRULES: 1, "AAA": 1})
	assert.Equal(t, []string{parser.LandmarkRULES, "AAA", "ZZZ"}, roles)

	r := result.NewLintResult("test")
	assert.False(t, hasTraceabilityErrors(r))
	r.AddError("E105", "bad", "loc")
	assert.True(t, hasTraceabilityErrors(r))
}
