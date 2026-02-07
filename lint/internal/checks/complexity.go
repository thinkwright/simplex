// Package checks provides linting checks for Simplex specifications.
package checks

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/brannn/simplex/lint/internal/parser"
	"github.com/brannn/simplex/lint/internal/result"
)

// ComplexityConfig holds thresholds for complexity checks.
type ComplexityConfig struct {
	MaxRules      int // Maximum number of RULES items (default: 15)
	MaxInputs     int // Maximum number of function inputs (default: 6)
	MaxRuleLength int // Maximum length of a single rule item (default: 200)
	MaxFunctions  int // Warning threshold for function count (default: 10)
}

// DefaultComplexityConfig returns the default complexity thresholds.
func DefaultComplexityConfig() ComplexityConfig {
	return ComplexityConfig{
		MaxRules:      15,
		MaxInputs:     6,
		MaxRuleLength: 200,
		MaxFunctions:  10,
	}
}

// ComplexityChecker performs complexity validation of Simplex specs.
type ComplexityChecker struct {
	config ComplexityConfig
}

// NewComplexityChecker creates a new ComplexityChecker with default config.
func NewComplexityChecker() *ComplexityChecker {
	return &ComplexityChecker{config: DefaultComplexityConfig()}
}

// NewComplexityCheckerWithConfig creates a ComplexityChecker with custom config.
func NewComplexityCheckerWithConfig(config ComplexityConfig) *ComplexityChecker {
	return &ComplexityChecker{config: config}
}

// Check performs all complexity checks on the parsed spec.
func (c *ComplexityChecker) Check(spec *parser.ParsedSpec, r *result.LintResult) {
	c.checkFunctionCount(spec, r)

	for _, fn := range spec.Functions {
		c.checkRulesComplexity(fn, r)
		c.checkInputCount(fn, r)
		c.checkRuleLength(fn, r)
		c.checkExampleCoverage(fn, r)
	}
}

// checkFunctionCount warns if there are too many functions.
// Warning W011: Spec has many FUNCTION blocks
func (c *ComplexityChecker) checkFunctionCount(spec *parser.ParsedSpec, r *result.LintResult) {
	if len(spec.Functions) > c.config.MaxFunctions {
		r.AddWarning("W011",
			fmt.Sprintf("Spec has %d FUNCTION blocks (consider splitting into multiple specs, max recommended: %d)",
				len(spec.Functions), c.config.MaxFunctions),
			"spec")
	}
}

// checkRulesComplexity checks if RULES block has too many items.
// Error E010: RULES block exceeds max items
func (c *ComplexityChecker) checkRulesComplexity(fn parser.FunctionBlock, r *result.LintResult) {
	rules := fn.GetRules()
	if rules == "" {
		return
	}

	count := CountRuleItems(rules)
	if count > c.config.MaxRules {
		r.AddError("E010",
			fmt.Sprintf("RULES block has %d items (max %d)", count, c.config.MaxRules),
			formatFunctionLocation(fn.Name))
	}
}

// checkInputCount checks if function has too many inputs.
// Error E011: FUNCTION has too many inputs
func (c *ComplexityChecker) checkInputCount(fn parser.FunctionBlock, r *result.LintResult) {
	if len(fn.Inputs) > c.config.MaxInputs {
		r.AddError("E011",
			fmt.Sprintf("FUNCTION has %d inputs (max %d)", len(fn.Inputs), c.config.MaxInputs),
			formatFunctionLocation(fn.Name))
	}
}

// checkRuleLength warns about individual rules that are too long.
// Warning W010: Single RULES item too long
func (c *ComplexityChecker) checkRuleLength(fn parser.FunctionBlock, r *result.LintResult) {
	rules := fn.GetRules()
	if rules == "" {
		return
	}

	items := ExtractRuleItems(rules)
	for i, item := range items {
		if len(item) > c.config.MaxRuleLength {
			r.AddWarningWithSuggestion("W010",
				fmt.Sprintf("RULES item %d exceeds %d characters (%d chars)",
					i+1, c.config.MaxRuleLength, len(item)),
				formatFunctionLocation(fn.Name),
				"Consider breaking this rule into multiple simpler rules",
				false)
		}
	}
}

// checkExampleCoverage checks if examples are fewer than branches.
// Error E012: EXAMPLES fewer than branch count
func (c *ComplexityChecker) checkExampleCoverage(fn parser.FunctionBlock, r *result.LintResult) {
	rules := fn.GetRules()
	examples := fn.GetExamples()

	if rules == "" || examples == "" {
		return
	}

	branchCount := CountBranches(rules)
	exampleCount := CountExamples(examples)

	if exampleCount < branchCount {
		r.AddError("E012",
			fmt.Sprintf("EXAMPLES has %d items but RULES has %d branches (examples should cover all branches)",
				exampleCount, branchCount),
			formatFunctionLocation(fn.Name))
	}
}

// CountRuleItems counts the number of rule items in a RULES block.
// Items are typically marked with - at the start of a line.
func CountRuleItems(rules string) int {
	items := ExtractRuleItems(rules)
	return len(items)
}

// ExtractRuleItems extracts individual rule items from a RULES block.
func ExtractRuleItems(rules string) []string {
	var items []string
	lines := strings.Split(rules, "\n")

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if len(trimmed) > 0 && trimmed[0] == '-' {
			// Remove the leading dash and trim
			item := strings.TrimSpace(trimmed[1:])
			if item != "" {
				items = append(items, item)
			}
		}
	}

	// If no dash-prefixed items found, count non-empty lines
	if len(items) == 0 {
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if trimmed != "" {
				items = append(items, trimmed)
			}
		}
	}

	return items
}

// CountExamples counts the number of examples in an EXAMPLES block.
func CountExamples(examples string) int {
	count := 0
	lines := strings.Split(examples, "\n")

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		// Examples typically start with ( or contain → or ->
		if len(trimmed) > 0 {
			if trimmed[0] == '(' ||
				strings.Contains(trimmed, "→") ||
				strings.Contains(trimmed, "->") {
				count++
			}
		}
	}

	return count
}

// Pre-compiled branch-counting patterns (compiled once, used per-call).
var (
	branchIfOrPattern       = regexp.MustCompile(`\bif\b[^,\n]*\bor\b`)
	branchIfElsePattern     = regexp.MustCompile(`\bif\b[^,\n]*(otherwise|else)\b`)
	branchSimpleIfPattern   = regexp.MustCompile(`\bif\b`)
	branchWhenPattern       = regexp.MustCompile(`\bwhen\b`)
	branchOptionalPattern   = regexp.MustCompile(`\boptionally\b`)
	branchEitherOrPattern   = regexp.MustCompile(`\beither\b[^,\n]*\bor\b`)
)

// CountBranches performs heuristic branch counting on RULES content.
// This counts conditional paths that should be covered by examples.
//
// Patterns that introduce branches:
//   - "if X" → 1 branch
//   - "if X or Y" → 2 branches
//   - "if X, otherwise Y" / "if X, else Y" → 2 branches
//   - "when X" → 1 branch
//   - "optionally" → 2 branches (with/without)
//   - "either X or Y" → 2 branches
func CountBranches(rulesContent string) int {
	// Normalize to lowercase for pattern matching
	content := strings.ToLower(rulesContent)
	count := 0

	// Pattern: "either X or Y" → 2 branches (counted first to avoid
	// "either...or" lines being double-counted by the if-or pattern)
	eitherOrMatches := branchEitherOrPattern.FindAllStringIndex(content, -1)
	count += len(eitherOrMatches) * 2

	// Build a set of positions consumed by "either...or" so we can
	// exclude them from subsequent if-pattern matching.
	isEitherLine := make(map[int]bool)
	lines := strings.Split(content, "\n")
	offset := 0
	for i, line := range lines {
		lineEnd := offset + len(line)
		for _, m := range eitherOrMatches {
			if m[0] >= offset && m[0] < lineEnd {
				isEitherLine[i] = true
			}
		}
		offset = lineEnd + 1 // +1 for the \n
	}

	// Count if-patterns only on lines that aren't "either...or" lines
	ifOrCount := 0
	ifElseCount := 0
	allIfCount := 0
	for i, line := range lines {
		if isEitherLine[i] {
			continue
		}
		ifOrCount += len(branchIfOrPattern.FindAllString(line, -1))
		ifElseCount += len(branchIfElsePattern.FindAllString(line, -1))
		allIfCount += len(branchSimpleIfPattern.FindAllString(line, -1))
	}

	// "if ... or ..." → 2 branches each
	count += ifOrCount * 2
	// "if ... otherwise/else ..." → 2 branches each
	count += ifElseCount * 2
	// Simple "if X" (not already counted as if-or or if-else) → 1 branch each
	simpleIfCount := allIfCount - ifOrCount - ifElseCount
	if simpleIfCount > 0 {
		count += simpleIfCount
	}

	// "when X" → 1 branch (only on non-either lines)
	for i, line := range lines {
		if isEitherLine[i] {
			continue
		}
		count += len(branchWhenPattern.FindAllString(line, -1))
	}

	// "optionally" → 2 branches
	count += len(branchOptionalPattern.FindAllString(content, -1)) * 2

	// Minimum of 1 branch if there are any rules
	if count == 0 && strings.TrimSpace(rulesContent) != "" {
		count = 1
	}

	return count
}

// GetConfig returns the current complexity configuration.
func (c *ComplexityChecker) GetConfig() ComplexityConfig {
	return c.config
}
