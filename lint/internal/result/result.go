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
	Fixable    bool    `json:"fixable"`              // can --fix resolve this?
}

// LintStats provides summary statistics for a linted spec.
type LintStats struct {
	Functions       int     `json:"functions"`
	Branches        int     `json:"branches"`
	Examples        int     `json:"examples"`
	CoveragePercent float64 `json:"coverage_percent,omitempty"`
}

// LintResult represents the complete linting output for a single file.
type LintResult struct {
	File     string      `json:"file"`
	Valid    bool        `json:"valid"`
	Errors   []LintError `json:"errors"`
	Warnings []LintError `json:"warnings"`
	Stats    LintStats   `json:"stats"`
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
	sb.WriteString(fmt.Sprintf("  %d error(s), %d warning(s)\n", len(r.Errors), len(r.Warnings)))

	if r.Valid {
		validColor := color.New(color.FgGreen, color.Bold)
		sb.WriteString("  Spec is ")
		validColor.Fprint(&sb, "VALID")
		sb.WriteString("\n")
	} else {
		invalidColor := color.New(color.FgRed, color.Bold)
		sb.WriteString("  Spec is ")
		invalidColor.Fprint(&sb, "INVALID")
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
	sb.WriteString(fmt.Sprintf("  %d/%d specs valid\n", m.TotalValid, m.TotalFiles))

	return sb.String()
}

// AllValid returns true if all results are valid.
func (m *MultiResult) AllValid() bool {
	return m.TotalValid == m.TotalFiles
}
