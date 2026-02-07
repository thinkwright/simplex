// Package checks provides linting checks for Simplex specifications.
package checks

import (
	"fmt"
	"strings"

	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// DeterminismChecker performs validation of DETERMINISM landmarks.
type DeterminismChecker struct{}

// NewDeterminismChecker creates a new DeterminismChecker.
func NewDeterminismChecker() *DeterminismChecker {
	return &DeterminismChecker{}
}

// Check performs all determinism-related checks on the parsed spec.
func (c *DeterminismChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) {
	for _, fn := range spec.Functions {
		if fn.HasDeterminism() {
			c.checkDeterminismStructure(fn, r)
		}
	}
}

// checkDeterminismStructure validates DETERMINISM landmark content.
// Error E070: DETERMINISM level must be strict, structural, or semantic
// Error E071: DETERMINISM seed must be a value or "from_input"
func (c *DeterminismChecker) checkDeterminismStructure(fn parser.FunctionBlock, r *result.LintResult) {
	content := fn.GetDeterminism()
	loc := formatFunctionLocation(fn.Name) + " DETERMINISM"

	level := ""

	// Parse DETERMINISM content
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}

		if strings.HasPrefix(trimmed, "level:") {
			level = strings.TrimSpace(strings.TrimPrefix(trimmed, "level:"))
		}
	}

	// Validate level - required and must be one of strict, structural, semantic
	if level == "" {
		r.AddError("E070", "DETERMINISM requires level field (strict, structural, or semantic)", loc)
	} else {
		validLevels := map[string]bool{
			"strict":     true,
			"structural": true,
			"semantic":   true,
		}
		if !validLevels[level] {
			r.AddError("E070", fmt.Sprintf("DETERMINISM level must be strict, structural, or semantic, got: %s", level), loc)
		}
	}
}
