package checks

import (
	"testing"

	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

func TestEvolutionChecker_BaselineWithoutEval(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E060 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E060" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E060 error for BASELINE without EVAL")
	}
}

func TestEvolutionChecker_BaselineWithEval(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: code
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have no errors
	if len(r.Errors) > 0 {
		t.Errorf("Expected no errors, got: %v", r.Errors)
	}
}

func TestEvolutionChecker_BaselineMissingReference(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass@5
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E050 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E050" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E050 error for BASELINE missing reference")
	}
}

func TestEvolutionChecker_BaselineMissingEvolve(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass@5
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E052 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E052" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E052 error for BASELINE missing evolve")
	}
}

func TestEvolutionChecker_InvalidPreserveThreshold(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass3
  evolve: pass@5
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E063 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E063" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E063 error for invalid preserve threshold")
	}
}

func TestEvolutionChecker_InvalidEvolveThreshold(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass5
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E064 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E064" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E064 error for invalid evolve threshold")
	}
}

func TestEvolutionChecker_InvalidGrading(t *testing.T) {
	spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: fuzzy
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have E065 error
	found := false
	for _, err := range r.Errors {
		if err.Code == "E065" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected E065 error for invalid grading type")
	}
}

func TestEvolutionChecker_ValidGradingTypes(t *testing.T) {
	gradingTypes := []string{"code", "model", "outcome"}

	for _, grading := range gradingTypes {
		spec := `
FUNCTION: migrate(config) → Result

BASELINE:
  reference: "v1.0"
  preserve:
    - existing API
  evolve:
    - add new feature

RULES:
  - migrate data

DONE_WHEN:
  - migration complete

EXAMPLES:
  (config) → result

ERRORS:
  - any → fail

EVAL:
  preserve: pass^3
  evolve: pass@5
  grading: ` + grading

		p := parser.NewParser()
		parsed := p.Parse(spec)
		r := result.NewLintResult("test")

		checker := NewEvolutionChecker()
		checker.Check(parsed, r)

		// Should have no errors
		if len(r.Errors) > 0 {
			t.Errorf("Expected no errors for grading=%s, got: %v", grading, r.Errors)
		}
	}
}

func TestEvolutionChecker_NoBaselineNoEval(t *testing.T) {
	spec := `
FUNCTION: add(a, b) → sum

RULES:
  - add numbers

DONE_WHEN:
  - result is sum

EXAMPLES:
  (2, 3) → 5

ERRORS:
  - any → fail
`

	p := parser.NewParser()
	parsed := p.Parse(spec)
	r := result.NewLintResult("test")

	checker := NewEvolutionChecker()
	checker.Check(parsed, r)

	// Should have no errors - BASELINE and EVAL are optional
	if len(r.Errors) > 0 {
		t.Errorf("Expected no errors for spec without BASELINE/EVAL, got: %v", r.Errors)
	}
}
