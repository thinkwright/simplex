// Package checks provides linting checks for Simplex specifications.
package checks

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// EvolutionChecker performs validation of BASELINE and EVAL landmarks.
type EvolutionChecker struct {
	// preservePattern matches pass^k notation (preserve threshold)
	preservePattern *regexp.Regexp
	// evolvePattern matches pass@k notation (evolve threshold)
	evolvePattern *regexp.Regexp
}

// NewEvolutionChecker creates a new EvolutionChecker.
func NewEvolutionChecker() *EvolutionChecker {
	return &EvolutionChecker{
		preservePattern: regexp.MustCompile(`^pass\^(\d+)$`),
		evolvePattern:   regexp.MustCompile(`^pass@(\d+)$`),
	}
}

// Check performs all evolution-related checks on the parsed spec.
func (c *EvolutionChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) {
	for _, fn := range spec.Functions {
		c.checkBaselineEvalPair(fn, r)
		if fn.HasBaseline() {
			c.checkBaselineStructure(fn, r)
		}
		if fn.HasEval() {
			c.checkEvalStructure(fn, r)
		}
	}
}

// checkBaselineEvalPair verifies that EVAL is present when BASELINE is present.
// Error E060: EVAL required when BASELINE present
func (c *EvolutionChecker) checkBaselineEvalPair(fn parser.FunctionBlock, r *result.LintResult) {
	if fn.HasBaseline() && !fn.HasEval() {
		loc := formatFunctionLocation(fn.Name)
		r.AddErrorWithSuggestion(
			"E060",
			"EVAL required when BASELINE present",
			loc,
			"Add EVAL: block with preserve and evolve thresholds (e.g., preserve: pass^3, evolve: pass@5)",
			true,
		)
	}
}

// checkBaselineStructure validates BASELINE landmark content.
// Error E050: BASELINE requires reference field
// Error E051: BASELINE requires preserve field
// Error E052: BASELINE requires evolve field
// Error E053: BASELINE preserve must contain at least one item
// Error E054: BASELINE evolve must contain at least one item
func (c *EvolutionChecker) checkBaselineStructure(fn parser.FunctionBlock, r *result.LintResult) {
	content := fn.GetBaseline()
	loc := formatFunctionLocation(fn.Name) + " BASELINE"

	hasReference := false
	hasPreserve := false
	hasEvolve := false
	preserveItems := 0
	evolveItems := 0

	// Parse BASELINE content looking for required fields
	lines := strings.Split(content, "\n")
	currentField := ""

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}

		// Check for field declarations
		if strings.HasPrefix(trimmed, "reference:") {
			hasReference = true
			currentField = "reference"
		} else if strings.HasPrefix(trimmed, "preserve:") {
			hasPreserve = true
			currentField = "preserve"
		} else if strings.HasPrefix(trimmed, "evolve:") {
			hasEvolve = true
			currentField = "evolve"
		} else if strings.HasPrefix(trimmed, "-") {
			// Count list items
			switch currentField {
			case "preserve":
				preserveItems++
			case "evolve":
				evolveItems++
			}
		}
	}

	if !hasReference {
		r.AddError("E050", "BASELINE requires reference field", loc)
	}

	if !hasPreserve {
		r.AddError("E051", "BASELINE requires preserve field", loc)
	} else if preserveItems == 0 {
		r.AddError("E053", "BASELINE preserve must contain at least one item", loc)
	}

	if !hasEvolve {
		r.AddError("E052", "BASELINE requires evolve field", loc)
	} else if evolveItems == 0 {
		r.AddError("E054", "BASELINE evolve must contain at least one item", loc)
	}
}

// checkEvalStructure validates EVAL landmark content.
// Error E061: EVAL requires preserve threshold when BASELINE present
// Error E062: EVAL requires evolve threshold when BASELINE present
// Error E063: preserve threshold must use pass^k notation
// Error E064: evolve threshold must use pass@k notation
// Error E065: grading must be code, model, or outcome
// Error E066: threshold k must be positive integer
func (c *EvolutionChecker) checkEvalStructure(fn parser.FunctionBlock, r *result.LintResult) {
	content := fn.GetEval()
	loc := formatFunctionLocation(fn.Name) + " EVAL"
	hasBaseline := fn.HasBaseline()

	preserveThreshold := ""
	evolveThreshold := ""
	grading := ""

	// Parse EVAL content
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}

		if strings.HasPrefix(trimmed, "preserve:") {
			preserveThreshold = strings.TrimSpace(strings.TrimPrefix(trimmed, "preserve:"))
		} else if strings.HasPrefix(trimmed, "evolve:") {
			evolveThreshold = strings.TrimSpace(strings.TrimPrefix(trimmed, "evolve:"))
		} else if strings.HasPrefix(trimmed, "grading:") {
			grading = strings.TrimSpace(strings.TrimPrefix(trimmed, "grading:"))
		}
	}

	// If BASELINE is present, preserve and evolve thresholds are required
	if hasBaseline {
		if preserveThreshold == "" {
			r.AddError("E061", "EVAL requires preserve threshold when BASELINE present", loc)
		}
		if evolveThreshold == "" {
			r.AddError("E062", "EVAL requires evolve threshold when BASELINE present", loc)
		}
	}

	// Validate preserve threshold notation (must be pass^k)
	if preserveThreshold != "" {
		if !c.preservePattern.MatchString(preserveThreshold) {
			r.AddError("E063", fmt.Sprintf("preserve threshold must use pass^k notation, got: %s", preserveThreshold), loc)
		}
	}

	// Validate evolve threshold notation (must be pass@k)
	if evolveThreshold != "" {
		if !c.evolvePattern.MatchString(evolveThreshold) {
			r.AddError("E064", fmt.Sprintf("evolve threshold must use pass@k notation, got: %s", evolveThreshold), loc)
		}
	}

	// Validate grading type
	if grading != "" {
		validGrading := map[string]bool{
			"code":    true,
			"model":   true,
			"outcome": true,
		}
		if !validGrading[grading] {
			r.AddError("E065", fmt.Sprintf("grading must be code, model, or outcome, got: %s", grading), loc)
		}
	}
}

