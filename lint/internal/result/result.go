// Package result provides types and formatting for lint results.
package result

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/fatih/color"
)

// Severity levels for lint issues
const (
	SeverityError   = "error"
	SeverityWarning = "warning"
)

// LintError represents a single linting issue.
type LintError struct {
	Code       string  `json:"code"`                 // e.g., "E001"
	Message    string  `json:"message"`              // human-readable description
	Location   string  `json:"location"`             // e.g., "FUNCTION filter_policies" or "line 42"
	Severity   string  `json:"severity"`             // "error" or "warning"
	Suggestion *string `json:"suggestion,omitempty"` // optional fix suggestion
	Fixable    bool    `json:"fixable"`              // suggestion is mechanical; no fixer is currently implemented
}

// LintStats provides summary statistics for a linted spec.
type LintStats struct {
	Functions         int                `json:"functions"`
	Branches          int                `json:"branches"`
	Examples          int                `json:"examples"`
	ExamplesPerBranch float64            `json:"examples_per_branch,omitempty"`
	Traceability      *TraceabilityStats `json:"traceability,omitempty"`
}

// TraceabilityStats summarizes author-declared example-to-contract links. It
// reports reference completeness, not proof that a mapping is semantically true.
type TraceabilityStats struct {
	Declared           bool           `json:"declared"`
	Identifiers        int            `json:"identifiers"`
	ExampleIdentifiers int            `json:"example_identifiers"`
	Links              int            `json:"links"`
	CoverableItems     int            `json:"coverable_items"`
	CoveredItems       int            `json:"covered_items"`
	UncoveredItems     int            `json:"uncovered_items"`
	UnlabelledItems    int            `json:"unlabelled_items"`
	UnlinkedExamples   int            `json:"unlinked_examples"`
	Complete           bool           `json:"complete"`
	ExampleKinds       map[string]int `json:"example_kinds,omitempty"`
}

// LintResult represents the complete linting output for a single file.
type LintResult struct {
	File                 string      `json:"file"`
	SpecificationVersion string      `json:"specification_version,omitempty"`
	SupportedVersion     string      `json:"supported_specification_version"`
	Valid                bool        `json:"valid"`
	Errors               []LintError `json:"errors"`
	Warnings             []LintError `json:"warnings"`
	Stats                LintStats   `json:"stats"`
}

// MultiResult aggregates results from multiple files.
type MultiResult struct {
	Results    []LintResult `json:"results"`
	TotalValid int          `json:"total_valid"`
	TotalFiles int          `json:"total_files"`
}

// NewLintResult creates a new LintResult for a file.
func NewLintResult(file string) *LintResult {
	return &LintResult{
		File:     file,
		Valid:    true,
		Errors:   []LintError{},
		Warnings: []LintError{},
	}
}

// AddError adds an error to the result and marks it invalid.
func (r *LintResult) AddError(code, message, location string) {
	r.Errors = append(r.Errors, LintError{
		Code:     code,
		Message:  message,
		Location: location,
		Severity: SeverityError,
		Fixable:  false,
	})
	r.Valid = false
}

// AddErrorWithSuggestion adds an error with a fix suggestion.
func (r *LintResult) AddErrorWithSuggestion(code, message, location, suggestion string, fixable bool) {
	r.Errors = append(r.Errors, LintError{
		Code:       code,
		Message:    message,
		Location:   location,
		Severity:   SeverityError,
		Suggestion: &suggestion,
		Fixable:    fixable,
	})
	r.Valid = false
}

// AddWarning adds a warning to the result (does not affect validity).
func (r *LintResult) AddWarning(code, message, location string) {
	r.Warnings = append(r.Warnings, LintError{
		Code:     code,
		Message:  message,
		Location: location,
		Severity: SeverityWarning,
		Fixable:  false,
	})
}

// AddWarningWithSuggestion adds a warning with a fix suggestion.
func (r *LintResult) AddWarningWithSuggestion(code, message, location, suggestion string, fixable bool) {
	r.Warnings = append(r.Warnings, LintError{
		Code:       code,
		Message:    message,
		Location:   location,
		Severity:   SeverityWarning,
		Suggestion: &suggestion,
		Fixable:    fixable,
	})
}

// ToJSON returns the result as formatted JSON.
func (r *LintResult) ToJSON() ([]byte, error) {
	return json.MarshalIndent(r, "", "  ")
}

// ToText returns the result as human-readable text with colors.
func (r *LintResult) ToText() string {
	var sb strings.Builder

	// Header
	headerColor := color.New(color.Bold)
	headerColor.Fprintf(&sb, "simplex-lint: %s\n", r.File)
	sb.WriteString("\n")

	// Errors
	if len(r.Errors) > 0 {
		errorColor := color.New(color.FgRed, color.Bold)
		errorColor.Fprintln(&sb, "ERRORS:")
		for _, e := range r.Errors {
			sb.WriteString(formatIssue(e, color.FgRed))
		}
		sb.WriteString("\n")
	}

	// Warnings
	if len(r.Warnings) > 0 {
		warnColor := color.New(color.FgYellow, color.Bold)
		warnColor.Fprintln(&sb, "WARNINGS:")
		for _, w := range r.Warnings {
			sb.WriteString(formatIssue(w, color.FgYellow))
		}
		sb.WriteString("\n")
	}

	// Summary
	summaryColor := color.New(color.Bold)
	summaryColor.Fprintln(&sb, "SUMMARY:")
	if r.SupportedVersion != "" {
		if r.SpecificationVersion == "" {
			sb.WriteString(fmt.Sprintf("  specification: unspecified (supported through %s)\n", r.SupportedVersion))
		} else {
			sb.WriteString(fmt.Sprintf("  specification: %s (supported through %s)\n", r.SpecificationVersion, r.SupportedVersion))
		}
	}
	if trace := r.Stats.Traceability; trace != nil {
		if !trace.Declared {
			sb.WriteString(fmt.Sprintf(
				"  traceability: not declared (%d identifier(s))\n",
				trace.Identifiers,
			))
		} else {
			status := "incomplete"
			if trace.Complete {
				status = "complete"
			}
			sb.WriteString(fmt.Sprintf(
				"  declared traceability: %s (%d/%d items, %d link(s))\n",
				status,
				trace.CoveredItems,
				trace.CoverableItems,
				trace.Links,
			))
		}
	}
	sb.WriteString(fmt.Sprintf("  %d error(s), %d warning(s)\n", len(r.Errors), len(r.Warnings)))

	if r.Valid {
		validColor := color.New(color.FgGreen, color.Bold)
		sb.WriteString("  Checks ")
		validColor.Fprint(&sb, "PASSED")
		sb.WriteString("\n")
	} else {
		invalidColor := color.New(color.FgRed, color.Bold)
		sb.WriteString("  Checks ")
		invalidColor.Fprint(&sb, "FAILED")
		sb.WriteString("\n")
	}

	return sb.String()
}

// formatIssue formats a single error or warning for text output.
func formatIssue(e LintError, c color.Attribute) string {
	var sb strings.Builder
	codeColor := color.New(c)

	sb.WriteString("  ")
	codeColor.Fprint(&sb, e.Code)
	sb.WriteString(fmt.Sprintf(" [%s] %s\n", e.Location, e.Message))

	if e.Suggestion != nil {
		sb.WriteString(fmt.Sprintf("       suggestion: %s\n", *e.Suggestion))
	}

	return sb.String()
}

// NewMultiResult creates a new MultiResult from individual results.
func NewMultiResult(results []LintResult) *MultiResult {
	valid := 0
	for _, r := range results {
		if r.Valid {
			valid++
		}
	}
	return &MultiResult{
		Results:    results,
		TotalValid: valid,
		TotalFiles: len(results),
	}
}

// ToJSON returns the multi-result as formatted JSON.
func (m *MultiResult) ToJSON() ([]byte, error) {
	return json.MarshalIndent(m, "", "  ")
}

// ToText returns the multi-result as human-readable text.
func (m *MultiResult) ToText() string {
	var sb strings.Builder

	for i, r := range m.Results {
		sb.WriteString(r.ToText())
		if i < len(m.Results)-1 {
			sb.WriteString("\n")
			sb.WriteString(strings.Repeat("-", 60))
			sb.WriteString("\n\n")
		}
	}

	// Overall summary
	sb.WriteString("\n")
	sb.WriteString(strings.Repeat("=", 60))
	sb.WriteString("\n")
	summaryColor := color.New(color.Bold)
	summaryColor.Fprintln(&sb, "OVERALL:")
	sb.WriteString(fmt.Sprintf("  %d/%d files passed\n", m.TotalValid, m.TotalFiles))

	return sb.String()
}

// AllValid returns true if all results are valid.
func (m *MultiResult) AllValid() bool {
	return m.TotalValid == m.TotalFiles
}
