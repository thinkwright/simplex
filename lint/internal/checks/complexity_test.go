package checks

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

func TestDefaultComplexityConfig(t *testing.T) {
	config := DefaultComplexityConfig()

	assert.Equal(t, 15, config.MaxRules)
	assert.Equal(t, 6, config.MaxInputs)
	assert.Equal(t, 200, config.MaxRuleLength)
	assert.Equal(t, 10, config.MaxFunctions)
}

func TestNewComplexityCheckerWithConfig(t *testing.T) {
	config := ComplexityConfig{
		MaxRules:      20,
		MaxInputs:     8,
		MaxRuleLength: 300,
		MaxFunctions:  15,
	}

	checker := NewComplexityCheckerWithConfig(config)
	assert.Equal(t, config, checker.GetConfig())
}

func TestComplexityChecker_E010_TooManyRules(t *testing.T) {
	// Create spec with 17 rules (exceeds default of 15)
	rules := make([]string, 17)
	for i := 0; i < 17; i++ {
		rules[i] = "  - rule " + string(rune('0'+i/10)) + string(rune('0'+i%10))
	}

	spec := `FUNCTION: complex() → result

RULES:
` + strings.Join(rules, "\n") + `

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	hasE010 := false
	for _, e := range r.Errors {
		if e.Code == "E010" {
			hasE010 = true
			assert.Contains(t, e.Message, "17 items")
			assert.Contains(t, e.Message, "max 15")
		}
	}
	assert.True(t, hasE010, "Expected E010 error for too many rules")
}

func TestComplexityChecker_E010_ExactlyAtLimit(t *testing.T) {
	// Create spec with exactly 15 rules (at limit, should pass)
	rules := make([]string, 15)
	for i := 0; i < 15; i++ {
		rules[i] = "  - rule " + string(rune('0'+i/10)) + string(rune('0'+i%10))
	}

	spec := `FUNCTION: at_limit() → result

RULES:
` + strings.Join(rules, "\n") + `

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	for _, e := range r.Errors {
		assert.NotEqual(t, "E010", e.Code, "Should not error at exactly the limit")
	}
}

func TestComplexityChecker_E011_TooManyInputs(t *testing.T) {
	spec := `FUNCTION: many_inputs(a, b, c, d, e, f, g, h) → result

RULES:
  - process all inputs

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2, 3, 4, 5, 6, 7, 8) → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	hasE011 := false
	for _, e := range r.Errors {
		if e.Code == "E011" {
			hasE011 = true
			assert.Contains(t, e.Message, "8 inputs")
			assert.Contains(t, e.Message, "max 6")
		}
	}
	assert.True(t, hasE011, "Expected E011 error for too many inputs")
}

func TestComplexityChecker_E011_ExactlyAtLimit(t *testing.T) {
	spec := `FUNCTION: at_limit(a, b, c, d, e, f) → result

RULES:
  - process inputs

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2, 3, 4, 5, 6) → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	for _, e := range r.Errors {
		assert.NotEqual(t, "E011", e.Code, "Should not error at exactly the limit")
	}
}

func TestComplexityChecker_W010_LongRule(t *testing.T) {
	longRule := "  - " + strings.Repeat("x", 250) // 250 chars exceeds 200 limit

	spec := `FUNCTION: long_rule() → result

RULES:
` + longRule + `

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	hasW010 := false
	for _, w := range r.Warnings {
		if w.Code == "W010" {
			hasW010 = true
			assert.Contains(t, w.Message, "exceeds 200 characters")
			assert.NotNil(t, w.Suggestion)
		}
	}
	assert.True(t, hasW010, "Expected W010 warning for long rule")
}

func TestComplexityChecker_W011_ManyFunctions(t *testing.T) {
	// Create spec with 12 functions (exceeds default of 10)
	var functions []string
	for i := 0; i < 12; i++ {
		fn := `FUNCTION: fn` + string(rune('0'+i/10)) + string(rune('0'+i%10)) + `() → result

RULES:
  - do something

DONE_WHEN:
  - done

EXAMPLES:
  () → ok

ERRORS:
  - fail`
		functions = append(functions, fn)
	}

	spec := strings.Join(functions, "\n\n")

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	hasW011 := false
	for _, w := range r.Warnings {
		if w.Code == "W011" {
			hasW011 = true
			assert.Contains(t, w.Message, "12 FUNCTION blocks")
		}
	}
	assert.True(t, hasW011, "Expected W011 warning for many functions")
}

func TestComplexityChecker_E012_InsufficientExamples(t *testing.T) {
	spec := `FUNCTION: branching() → result

RULES:
  - if input is A, return X
  - if input is B, return Y
  - if input is C or D, return Z

DONE_WHEN:
  - correct result returned

EXAMPLES:
  (A) → X

ERRORS:
  - fail`
	// Has 4 branches but only 1 example

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	hasE012 := false
	for _, e := range r.Errors {
		if e.Code == "E012" {
			hasE012 = true
			assert.Contains(t, e.Message, "1 items")
			assert.Contains(t, e.Message, "branches")
		}
	}
	assert.True(t, hasE012, "Expected E012 error for insufficient examples")
}

func TestComplexityChecker_E012_SufficientExamples(t *testing.T) {
	spec := `FUNCTION: branching() → result

RULES:
  - if input is A, return X
  - if input is B, return Y

DONE_WHEN:
  - correct result returned

EXAMPLES:
  (A) → X
  (B) → Y
  (C) → default

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()
	checker.Check(parsed, r)

	for _, e := range r.Errors {
		assert.NotEqual(t, "E012", e.Code, "Should not error when examples >= branches")
	}
}

func TestComplexityChecker_CustomConfig(t *testing.T) {
	config := ComplexityConfig{
		MaxRules:      5,
		MaxInputs:     3,
		MaxRuleLength: 100,
		MaxFunctions:  2,
	}

	spec := `FUNCTION: test(a, b, c, d) → result

RULES:
  - rule 1
  - rule 2
  - rule 3
  - rule 4
  - rule 5
  - rule 6

DONE_WHEN:
  - done

EXAMPLES:
  (1, 2, 3, 4) → ok

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityCheckerWithConfig(config)
	checker.Check(parsed, r)

	// Should have E010 (6 rules > 5 max) and E011 (4 inputs > 3 max)
	codes := make(map[string]bool)
	for _, e := range r.Errors {
		codes[e.Code] = true
	}
	assert.True(t, codes["E010"], "Expected E010 with custom config")
	assert.True(t, codes["E011"], "Expected E011 with custom config")
}

func TestCountRuleItems(t *testing.T) {
	tests := []struct {
		name     string
		rules    string
		expected int
	}{
		{
			name:     "dash prefixed items",
			rules:    "- rule 1\n- rule 2\n- rule 3",
			expected: 3,
		},
		{
			name:     "indented dash items",
			rules:    "  - rule 1\n  - rule 2",
			expected: 2,
		},
		{
			name:     "no dashes fallback to lines",
			rules:    "rule 1\nrule 2\nrule 3",
			expected: 3,
		},
		{
			name:     "empty",
			rules:    "",
			expected: 0,
		},
		{
			name:     "whitespace only",
			rules:    "   \n   \n",
			expected: 0,
		},
		{
			name:     "mixed content",
			rules:    "- item 1\n\n- item 2\n- item 3",
			expected: 3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			count := CountRuleItems(tt.rules)
			assert.Equal(t, tt.expected, count)
		})
	}
}

func TestExtractRuleItems(t *testing.T) {
	rules := "  - first rule\n  - second rule\n  - third rule"
	items := ExtractRuleItems(rules)

	require.Len(t, items, 3)
	assert.Equal(t, "first rule", items[0])
	assert.Equal(t, "second rule", items[1])
	assert.Equal(t, "third rule", items[2])
}

func TestCountExamples(t *testing.T) {
	tests := []struct {
		name     string
		examples string
		expected int
	}{
		{
			name:     "parentheses start",
			examples: "(1, 2) → 3\n(0, 0) → 0",
			expected: 2,
		},
		{
			name:     "arrow only",
			examples: "input → output\nanother → result",
			expected: 2,
		},
		{
			name:     "ascii arrow",
			examples: "(x) -> y\n(a) -> b",
			expected: 2,
		},
		{
			name:     "empty",
			examples: "",
			expected: 0,
		},
		{
			name:     "mixed with blank lines",
			examples: "(1) → a\n\n(2) → b\n\n(3) → c",
			expected: 3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			count := CountExamples(tt.examples)
			assert.Equal(t, tt.expected, count)
		})
	}
}

func TestCountBranches(t *testing.T) {
	tests := []struct {
		name     string
		rules    string
		expected int
	}{
		{
			name:     "simple if",
			rules:    "- if input is valid, process it",
			expected: 1,
		},
		{
			name:     "if with or",
			rules:    "- if input is A or B, return X",
			expected: 2,
		},
		{
			name:     "if with otherwise",
			rules:    "- if input is valid then process otherwise reject",
			expected: 2,
		},
		{
			name:     "if with else keyword",
			rules:    "- if condition then X else Y",
			expected: 2,
		},
		{
			name:     "when clause",
			rules:    "- when ready, start processing",
			expected: 1,
		},
		{
			name:     "optionally",
			rules:    "- optionally include metadata",
			expected: 2,
		},
		{
			name:     "either or",
			rules:    "- either return success or fail with error",
			expected: 2,
		},
		{
			name:     "multiple branches",
			rules:    "- if A, do X\n- if B, do Y\n- if C or D, do Z",
			expected: 4, // 1 + 1 + 2
		},
		{
			name:     "no branches",
			rules:    "- process the input\n- return result",
			expected: 1, // minimum 1
		},
		{
			name:     "empty",
			rules:    "",
			expected: 0,
		},
		{
			name:     "complex mixed",
			rules:    "- if valid, process\n- when complete, notify\n- optionally log\n- either succeed or fail",
			expected: 6, // 1 + 1 + 2 + 2 (no minimum added when there are branches)
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			count := CountBranches(tt.rules)
			assert.Equal(t, tt.expected, count, "Rules: %s", tt.rules)
		})
	}
}

func TestComplexityChecker_NoRulesOrExamples(t *testing.T) {
	// Test that checker handles missing RULES/EXAMPLES gracefully
	// (structural checker would catch this, but complexity shouldn't crash)
	spec := `FUNCTION: empty() → result

DONE_WHEN:
  - done

ERRORS:
  - fail`

	p := parser.NewParser()
	parsed := p.Parse(spec)

	r := result.NewLintResult("test.md")
	checker := NewComplexityChecker()

	// Should not panic
	checker.Check(parsed, r)

	// No E010, E012 errors (missing landmarks are structural errors)
	for _, e := range r.Errors {
		assert.NotEqual(t, "E010", e.Code)
		assert.NotEqual(t, "E012", e.Code)
	}
}
