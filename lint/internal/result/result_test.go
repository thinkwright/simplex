package result

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewLintResult(t *testing.T) {
	r := NewLintResult("test.md")

	assert.Equal(t, "test.md", r.File)
	assert.True(t, r.Valid)
	assert.Empty(t, r.Errors)
	assert.Empty(t, r.Warnings)
}

func TestLintResult_AddError(t *testing.T) {
	r := NewLintResult("test.md")

	r.AddError("E001", "No FUNCTION block found", "spec")

	assert.False(t, r.Valid)
	require.Len(t, r.Errors, 1)
	assert.Equal(t, "E001", r.Errors[0].Code)
	assert.Equal(t, "No FUNCTION block found", r.Errors[0].Message)
	assert.Equal(t, "spec", r.Errors[0].Location)
	assert.Equal(t, SeverityError, r.Errors[0].Severity)
	assert.Nil(t, r.Errors[0].Suggestion)
	assert.False(t, r.Errors[0].Fixable)
}

func TestLintResult_AddErrorWithSuggestion(t *testing.T) {
	r := NewLintResult("test.md")

	r.AddErrorWithSuggestion(
		"E005",
		"FUNCTION missing ERRORS landmark",
		"FUNCTION validate_input",
		"Add ERRORS: block with at least default error handling",
		true,
	)

	assert.False(t, r.Valid)
	require.Len(t, r.Errors, 1)
	assert.Equal(t, "E005", r.Errors[0].Code)
	require.NotNil(t, r.Errors[0].Suggestion)
	assert.Equal(t, "Add ERRORS: block with at least default error handling", *r.Errors[0].Suggestion)
	assert.True(t, r.Errors[0].Fixable)
}

func TestLintResult_AddWarning(t *testing.T) {
	r := NewLintResult("test.md")

	r.AddWarning("W010", "Single RULES item exceeds 200 characters", "FUNCTION process, RULES item 3")

	// Warnings don't affect validity
	assert.True(t, r.Valid)
	require.Len(t, r.Warnings, 1)
	assert.Equal(t, "W010", r.Warnings[0].Code)
	assert.Equal(t, SeverityWarning, r.Warnings[0].Severity)
}

func TestLintResult_MultipleIssues(t *testing.T) {
	r := NewLintResult("test.md")

	r.AddError("E001", "error 1", "loc1")
	r.AddError("E002", "error 2", "loc2")
	r.AddWarning("W001", "warning 1", "loc3")

	assert.False(t, r.Valid)
	assert.Len(t, r.Errors, 2)
	assert.Len(t, r.Warnings, 1)
}

func TestLintResult_ToJSON(t *testing.T) {
	r := NewLintResult("test.md")
	r.AddError("E001", "No FUNCTION block found", "spec")
	r.Stats = LintStats{Functions: 0, Branches: 0, Examples: 0}

	jsonBytes, err := r.ToJSON()
	require.NoError(t, err)

	// Verify it's valid JSON
	var parsed map[string]interface{}
	err = json.Unmarshal(jsonBytes, &parsed)
	require.NoError(t, err)

	assert.Equal(t, "test.md", parsed["file"])
	assert.Equal(t, false, parsed["valid"])
}

func TestLintResult_ToText(t *testing.T) {
	r := NewLintResult("test.md")
	r.AddError("E001", "No FUNCTION block found", "spec")
	r.AddWarning("W001", "Unrecognized landmark", "line 15")

	text := r.ToText()

	assert.Contains(t, text, "simplex-lint: test.md")
	assert.Contains(t, text, "ERRORS:")
	assert.Contains(t, text, "E001")
	assert.Contains(t, text, "No FUNCTION block found")
	assert.Contains(t, text, "WARNINGS:")
	assert.Contains(t, text, "W001")
	assert.Contains(t, text, "INVALID")
}

func TestLintResult_ToText_Valid(t *testing.T) {
	r := NewLintResult("valid.md")

	text := r.ToText()

	assert.Contains(t, text, "simplex-lint: valid.md")
	assert.Contains(t, text, "0 error(s), 0 warning(s)")
	assert.Contains(t, text, "VALID")
	assert.NotContains(t, text, "INVALID")
}

func TestLintResult_ToText_WithSuggestion(t *testing.T) {
	r := NewLintResult("test.md")
	r.AddErrorWithSuggestion("E005", "Missing ERRORS", "FUNCTION foo", "Add ERRORS block", true)

	text := r.ToText()

	assert.Contains(t, text, "suggestion: Add ERRORS block")
}

func TestNewMultiResult(t *testing.T) {
	r1 := NewLintResult("valid.md")
	r2 := NewLintResult("invalid.md")
	r2.AddError("E001", "error", "loc")

	m := NewMultiResult([]LintResult{*r1, *r2})

	assert.Equal(t, 2, m.TotalFiles)
	assert.Equal(t, 1, m.TotalValid)
	assert.False(t, m.AllValid())
}

func TestMultiResult_AllValid(t *testing.T) {
	r1 := NewLintResult("valid1.md")
	r2 := NewLintResult("valid2.md")

	m := NewMultiResult([]LintResult{*r1, *r2})

	assert.True(t, m.AllValid())
}

func TestMultiResult_ToJSON(t *testing.T) {
	r1 := NewLintResult("test1.md")
	r2 := NewLintResult("test2.md")
	r2.AddError("E001", "error", "loc")

	m := NewMultiResult([]LintResult{*r1, *r2})

	jsonBytes, err := m.ToJSON()
	require.NoError(t, err)

	var parsed map[string]interface{}
	err = json.Unmarshal(jsonBytes, &parsed)
	require.NoError(t, err)

	assert.Equal(t, float64(2), parsed["total_files"])
	assert.Equal(t, float64(1), parsed["total_valid"])
}

func TestMultiResult_ToText(t *testing.T) {
	r1 := NewLintResult("test1.md")
	r2 := NewLintResult("test2.md")
	r2.AddError("E001", "error", "loc")

	m := NewMultiResult([]LintResult{*r1, *r2})

	text := m.ToText()

	assert.Contains(t, text, "test1.md")
	assert.Contains(t, text, "test2.md")
	assert.Contains(t, text, "OVERALL:")
	assert.Contains(t, text, "1/2 specs valid")
	// Should have separator between results
	assert.True(t, strings.Contains(text, "----"))
}

func TestLintResult_AddWarningWithSuggestion(t *testing.T) {
	r := NewLintResult("test.md")

	r.AddWarningWithSuggestion(
		"W010",
		"Rule is too long",
		"FUNCTION test, RULES item 1",
		"Consider breaking into multiple rules",
		false,
	)

	// Warnings don't affect validity
	assert.True(t, r.Valid)
	require.Len(t, r.Warnings, 1)
	assert.Equal(t, "W010", r.Warnings[0].Code)
	assert.Equal(t, SeverityWarning, r.Warnings[0].Severity)
	require.NotNil(t, r.Warnings[0].Suggestion)
	assert.Equal(t, "Consider breaking into multiple rules", *r.Warnings[0].Suggestion)
	assert.False(t, r.Warnings[0].Fixable)
}

func TestLintResult_ToText_OnlyErrors(t *testing.T) {
	r := NewLintResult("test.md")
	r.AddError("E001", "error message", "location")

	text := r.ToText()

	assert.Contains(t, text, "ERRORS:")
	assert.Contains(t, text, "E001")
	assert.NotContains(t, text, "WARNINGS:") // No warnings section when empty
}

func TestLintResult_ToText_OnlyWarnings(t *testing.T) {
	r := NewLintResult("test.md")
	r.AddWarning("W001", "warning message", "location")

	text := r.ToText()

	assert.NotContains(t, text, "ERRORS:") // No errors section when empty
	assert.Contains(t, text, "WARNINGS:")
	assert.Contains(t, text, "W001")
	assert.Contains(t, text, "VALID") // Still valid with only warnings
}

func TestMultiResult_SingleFile(t *testing.T) {
	r := NewLintResult("single.md")
	m := NewMultiResult([]LintResult{*r})

	assert.Equal(t, 1, m.TotalFiles)
	assert.Equal(t, 1, m.TotalValid)
	assert.True(t, m.AllValid())
}

func TestMultiResult_AllInvalid(t *testing.T) {
	r1 := NewLintResult("invalid1.md")
	r1.AddError("E001", "error", "loc")
	r2 := NewLintResult("invalid2.md")
	r2.AddError("E002", "error", "loc")

	m := NewMultiResult([]LintResult{*r1, *r2})

	assert.Equal(t, 2, m.TotalFiles)
	assert.Equal(t, 0, m.TotalValid)
	assert.False(t, m.AllValid())
}

func TestLintStats_Zero(t *testing.T) {
	r := NewLintResult("test.md")

	assert.Equal(t, 0, r.Stats.Functions)
	assert.Equal(t, 0, r.Stats.Branches)
	assert.Equal(t, 0, r.Stats.Examples)
	assert.Equal(t, 0.0, r.Stats.CoveragePercent)
}

func TestLintResult_ToJSON_WithStats(t *testing.T) {
	r := NewLintResult("test.md")
	r.Stats = LintStats{
		Functions:       3,
		Branches:        10,
		Examples:        8,
		CoveragePercent: 80.0,
	}

	jsonBytes, err := r.ToJSON()
	require.NoError(t, err)

	jsonStr := string(jsonBytes)
	assert.Contains(t, jsonStr, `"functions": 3`)
	assert.Contains(t, jsonStr, `"branches": 10`)
	assert.Contains(t, jsonStr, `"examples": 8`)
	assert.Contains(t, jsonStr, `"coverage_percent": 80`)
}
